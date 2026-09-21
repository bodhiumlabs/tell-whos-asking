"""
forum_host_classifier.py
========================

Pattern-based classifier that decides whether a web *host* is a genuine
user-generated-content source (forum / Q&A / community / discussion).

Why this exists
---------------
Question occurrences are tagged with the host they were found on. The host
space is a flat long tail dominated by storefronts, brand pages, SaaS landing
pages and SEO/content mills that emit boilerplate rather than real questions,
and only a small fraction of hosts are genuine UGC. Per-host hand-labelling is
impossible at that scale, so this module generalises by *pattern* (curated
platform sets + structural conventions), not memorisation.

Design philosophy: PRECISION OVER RECALL for ``is_genuine_ugc``.
There is volume to spare, so dropping a real forum is cheap and admitting a
content farm is expensive. Therefore:

  * ``genuine_ugc`` is granted ONLY by (a) a curated set of known platforms or
    (b) a small set of high-precision structural signals (a ``forum``/
    ``community``/``boards`` style subdomain, or ``forum`` inside the
    registrable domain, or a forum-shaped URL path).
  * A bare ``answers``/``ask`` substring NEVER grants ``genuine_ugc`` -- those
    are the exact strings SEO Q&A mills hide behind. They route to
    ``seo_content_farm`` instead.
  * Free-TLD / fake / crypto / gambling / adult spam is stripped first, so a
    fake forum on a ``.ml`` domain can never slip through as genuine.
  * When in doubt we return ``unknown`` (surfaced for human review), never a
    speculative ``genuine_ugc``.

Public API
----------
    classify_host(host: str) -> str          # one of CATEGORIES
    is_genuine_ugc(host: str) -> bool         # True only for genuine forum/Q&A/community

The non-UGC categories (commercial_store / brand_marketing / saas_product /
editorial_review) are best-effort and coarse -- a host string alone usually
cannot separate "small brand store" from "marketing page". They exist to make
the validation distribution informative; the long tail intentionally lands in
``unknown``. Only ``genuine_ugc`` (and, secondarily, the two exclusion buckets
``seo_content_farm`` / ``spam_low_quality``) are tuned for precision.
"""

from __future__ import annotations

import re

CATEGORIES = (
    "genuine_ugc",        # forum / Q&A / community / discussion -- the keep set
    "editorial_review",   # legit independent review / editorial / news / tech media
    "commercial_store",   # storefront / marketplace
    "brand_marketing",    # single-brand site / marketing page
    "saas_product",       # software product / SaaS landing or app
    "seo_content_farm",   # scraped-answer / how-to / article mill masquerading as Q&A
    "spam_low_quality",   # free-TLD, crypto, gambling, adult, test/fake forum, link spam
    "unknown",            # could not classify with confidence -> human review
)

PRIORITY = "PRECISION OVER RECALL on genuine_ugc"


# ---------------------------------------------------------------------------
# Host normalisation + registrable-domain extraction
# ---------------------------------------------------------------------------
# We do not ship a full Public Suffix List. A compact set of multi-label public
# suffixes covers the ccTLD shapes that actually appear in the corpus. Getting
# the registrable label right matters because most of our signals key off it.

_TWO_LEVEL_SUFFIXES = {
    # United Kingdom
    "co.uk", "org.uk", "me.uk", "ac.uk", "gov.uk", "net.uk", "sch.uk", "ltd.uk",
    # Australia / NZ
    "com.au", "net.au", "org.au", "edu.au", "gov.au", "id.au",
    "co.nz", "net.nz", "org.nz", "govt.nz", "ac.nz", "geek.nz",
    # Brazil
    "com.br", "net.br", "org.br", "gov.br", "edu.br", "adv.br", "blog.br",
    # South Africa
    "co.za", "org.za", "net.za", "gov.za", "ac.za", "web.za",
    # Turkey
    "com.tr", "net.tr", "org.tr", "gov.tr", "edu.tr", "k12.tr",
    # India
    "co.in", "net.in", "org.in", "gov.in", "ac.in", "edu.in", "firm.in",
    # SE Asia
    "co.id", "or.id", "ac.id", "go.id", "web.id", "my.id", "sch.id",
    "com.sg", "com.my", "com.ph", "com.vn", "edu.vn", "gov.vn",
    "go.th", "ac.th", "or.th", "sc.th", "in.th",
    # Other common
    "com.mx", "com.co", "com.pk", "com.ng", "edu.ng", "gov.ng",
    "co.il", "co.kr", "co.jp", "com.cn", "com.hk", "com.tw", "com.kw",
    "com.ua", "com.gt", "com.pe", "com.mt", "co.nl",
    "co.ke", "or.ke", "ac.ke", "gov.lk", "gov.bt", "edu.bt",
    "gob.pe", "ac.rs", "ac.ua", "edu.eg", "ac.ng", "k12.al.us",
}


def _strip_to_host(raw: str) -> tuple[str, str]:
    """Return (host, path) from a raw host or URL string.

    The public API takes a *host*, but we accept full URLs defensively so the
    forum-shaped *path* signals (``viewtopic``, ``/showthread``, ``/r/`` ...)
    can fire if a caller passes one. For bare hosts ``path`` is "".
    """
    s = raw.strip().lower()
    if not s:
        return "", ""
    # drop scheme
    if "://" in s:
        s = s.split("://", 1)[1]
    # drop userinfo
    if "@" in s.split("/", 1)[0]:
        s = s.split("@", 1)[1]
    # split host / path
    if "/" in s:
        host, path = s.split("/", 1)
        path = "/" + path
    else:
        host, path = s, ""
    # drop port and trailing dot
    host = host.split(":", 1)[0].rstrip(".")
    # leading www. is noise for classification
    while host.startswith("www."):
        host = host[4:]
    return host, path


def _split_host(host: str):
    """Return (registered_label, etld1, suffix, subdomain_labels)."""
    labels = [l for l in host.split(".") if l != ""]
    if len(labels) < 2:
        return (labels[0] if labels else ""), host, "", []
    last2 = ".".join(labels[-2:])
    if last2 in _TWO_LEVEL_SUFFIXES:
        suffix_len = 2
    else:
        suffix_len = 1
    reg_idx = len(labels) - suffix_len - 1
    if reg_idx < 0:  # the whole host *is* a public suffix
        return "", host, ".".join(labels[-suffix_len:]), []
    suffix = ".".join(labels[-suffix_len:])
    registered_label = labels[reg_idx]
    etld1 = ".".join(labels[reg_idx:])
    subdomains = labels[:reg_idx]
    return registered_label, etld1, suffix, subdomains


# ---------------------------------------------------------------------------
# Layer 1 -- spam / junk (runs FIRST so junk can't be rescued by a forum word)
# ---------------------------------------------------------------------------

# Free TLDs handed out for free; in this corpus they are ~entirely throwaway
# spam (fake forums, redirect farms). Treat as spam regardless of any forum word.
_FREE_SPAM_TLDS = {"ml", "gq", "tk", "cf", "ga"}

# Crypto/airdrop spam networks. They appear either as
#   <coinname>.<random>.<tld>   (token name in the subdomain)  e.g. veruscoin.ecvd.eu
#   <random-coin-words>.xyz                                    e.g. mooncryptomoney.xyz
_CRYPTO_RE = re.compile(
    r"(?:^|[-.])(?:coin|token|crypto|bitcoin|btc|ethereum|eth|defi|nft|dao|"
    r"swap|airdrop|mining|miner|staking|yield|wallet|moon\w*token|"
    r"cryptomoney|moneycoin|tokenmoon)"
)
# TLDs heavily abused by the crypto/airdrop spam network seen in this corpus.
_CRYPTO_SUSPECT_TLDS = {"xyz", "pw", "icu", "top", "site", "online", "best", "space", "eu"}

# Gambling / casino / adult spam keywords (token-level).
_GAMBLING_RE = re.compile(
    r"(?:^|[-.])(?:togel|judi|slot(?:s|gacor)?|kasino|casino|poker|qq\d*|bandar|"
    r"pkv|dominoqq|tangkas|sbobet|maxwin|gacor)(?:$|[-.0-9])"
)
_ADULT_RE = re.compile(
    r"(?:^|[-.])(?:porn|xxx|hentai|escort|camgirl|ladyboycam|jerkmate|sexcam|"
    r"erotica|rape-stories|adultsextoys)"
)

# Throwaway free app hosts with gibberish prefixes, and obvious test/fake forums.
_FAKE_FORUM_RE = re.compile(r"forum.*test|test.*forum|fakeforum")
_RANDOM_APP_HOST_TLDS = {"web.app", "netlify.app"}  # subdomain is usually a random hash


def _looks_random(label: str) -> bool:
    """Heuristic: gibberish / hash-like subdomain (e.g. networkloadsbvkgq)."""
    if len(label) < 10:
        return False
    # long, no vowels-run, looks like base36 noise
    vowels = sum(c in "aeiou" for c in label)
    return vowels <= max(1, len(label) // 8) and label.isalnum()


def _is_spam(host: str, registered_label: str, suffix: str, subdomains: list[str]) -> bool:
    tld = suffix.split(".")[-1]
    if tld in _FREE_SPAM_TLDS:
        return True
    if _FAKE_FORUM_RE.search(host) or ".xooit." in ("." + host + "."):
        return True
    if _GAMBLING_RE.search(host) or _ADULT_RE.search(host):
        return True
    # crypto spam: keyword anywhere in host, on a suspect TLD
    if tld in _CRYPTO_SUSPECT_TLDS and _CRYPTO_RE.search(host):
        return True
    # crypto-words registered domain on a suspect TLD even without subdomain
    if tld in {"xyz", "pw", "icu"} and _CRYPTO_RE.search(registered_label):
        return True
    # random-hash app hosts
    last2 = ".".join(suffix.split(".")) if suffix else ""
    if last2 in _RANDOM_APP_HOST_TLDS and subdomains and _looks_random(subdomains[-1]):
        return True
    return False


# ---------------------------------------------------------------------------
# Layer 2 -- curated GENUINE platforms (trusted; override SEO/structural heuristics)
# ---------------------------------------------------------------------------

# Matched on the registrable label (any subdomain allowed). Globally known
# forum / Q&A / community platforms.
_GENUINE_REGISTERED = {
    # Q&A networks
    "reddit", "quora", "stackoverflow", "superuser", "serverfault",
    "askubuntu", "mathoverflow", "stackapps", "stackexchange",
    "experts-exchange", "fixya",
    # community / discussion / forum hubs
    "metafilter", "houzz", "mumsnet", "netmums", "digitalspy",
    "avforums", "avsforum", "xda-developers", "physicsforums", "bogleheads",
    "city-data", "tripadvisor", "freerepublic",
    # well-known independent niche forums (manually verified as genuine UGC).
    # NOTE: this is deliberately a *short, hand-checked* list -- niche forums not
    # here fall to `unknown` by design (recall gap we accept for precision).
    "mobileread", "hotrodders", "terrylove", "thefiringline", "hvac-talk",
}

# Matched on the full host (parent domain is NOT genuine, only this subdomain is).
_GENUINE_FULL_HOST = {
    "answers.yahoo.com",      # genuine UGC Q&A (defunct but real); yahoo.com is a portal
    "answers.microsoft.com",  # MS community Q&A
    "groups.google.com",      # Usenet / Google Groups discussion
    "news.ycombinator.com",   # Hacker News
}

# Matched on the exact eTLD+1.
_GENUINE_ETLD1 = {"redd.it"}

# Forum-hosting providers: the actual forum lives on a subdomain of these.
# e.g. <board>.proboards.com, <board>.forumotion.net
_FORUM_HOST_PROVIDERS = {
    "proboards", "forumotion", "forumactif", "runboard", "freeforums",
    "zetaboards", "lefora", "createaforum", "boardhost", "myfastforum",
}


def _is_curated_genuine(host, registered_label, etld1, subdomains) -> bool:
    if host in _GENUINE_FULL_HOST:
        return True
    if etld1 in _GENUINE_ETLD1:
        return True
    if registered_label in _GENUINE_REGISTERED:
        return True
    if registered_label in _FORUM_HOST_PROVIDERS and subdomains:
        return True
    return False


# ---------------------------------------------------------------------------
# Layer 3 -- SEO content farms (runs BEFORE structural genuine patterns)
# ---------------------------------------------------------------------------
# These mills hide behind answer/how-to/tips/facts/question wording. The named
# examples in the spec MUST land here, not in genuine_ugc.

# Explicit known offenders (registrable label) -- the spec's required examples
# plus clear-cut farms observed in the sample. The token regex below generalises
# beyond this list.
_SEO_BLOCKLIST = {
    # spec-required
    "psichologyanswers", "sage-answers", "answers", "seniorcare2share",
    "howtodiscuss", "howto", "how", "moviecultists", "remodelormove",
    "easierwithpractice",
    # clear sample farms with no generic token to key off
    "bikehike", "mvorganizing", "mv-organizing", "popularask", "yourgametips",
    "answer-all", "instantanswers", "similaranswer", "cementanswers",
    "answerstoall", "philosophy-question", "sociology-tips", "short-fact",
    "theknowledgeburrow", "findanyanswer", "gegcalculators", "ru-facts",
    "interesting-information", "whyienjoy", "practiceadvices", "quitechefy",
    "ccnaanswers", "experts123", "queryuniversity", "allquestion",
    "boardgamestips", "whomadewhat", "howtocreate", "howtocrazy",
    "seniorcareto", "answersinformer", "answer-informer", "consumersolution",
    "calendar-canada", "topcookingstories", "recipes4day", "interviewarea",
    "yourgametips", "similaranswers", "newsbasis", "thekeyboardreview",
}

# Generalising token regex applied to the registrable label. A match means
# "looks like a Q&A / how-to / tips / facts content mill".
_SEO_TOKEN_RE = re.compile(
    r"answers?"            # answer, answers, *answers, answer-*
    r"|knowledge"          # knowledgeburrow, knowledgetimer
    r"|how-?to"            # howto.org, howtodiscuss, howtocreate
    r"|^how$"              # how.co
    r"|2share|2know"       # seniorcare2share
    r"|organizing"         # mvorganizing
    r"|questions?$|-questions?"   # philosophy-question, allquestion
    r"|popularask"
    r"|game-?tips|home-?tips|life-?tips|tips$"   # *tips mills (not generic 'tips' substring)
    r"|sociology-?tips"
    r"|short-?fact|ru-?fact|funfacts?$"
    r"|practiceadvice|easierwithpractice"
)

# Article-spinning / scraped-doc aggregators -> also content farms.
_ARTICLE_MILL = {
    "articlesfactory", "articlesbase", "ezinearticles", "isnare", "articledaisy",
    "sooperarticles", "123articleonline", "articlesdb", "articlesurfing",
    "apsense", "zupyak", "bookriff", "hubpages", "wallinside", "pearltrees",
    "docstoc", "issuu", "slideshare", "scribd", "articlesonline", "pointshop",
}


def _is_seo_farm(registered_label: str) -> bool:
    if registered_label in _SEO_BLOCKLIST:
        return True
    if registered_label in _ARTICLE_MILL:
        return True
    if _SEO_TOKEN_RE.search(registered_label):
        return True
    return False


# ---------------------------------------------------------------------------
# Layer 4 -- structural GENUINE patterns (high precision, generalising)
# ---------------------------------------------------------------------------

# Subdomain labels that reliably denote a forum/community section.
_FORUM_SUBDOMAIN_LABELS = {
    "forum", "forums", "community", "communities", "board", "boards",
    "talk", "discuss", "discussion", "discussions", "foro", "foros", "bbs",
}

# Forum-shaped URL path fragments (only fire if a path was supplied).
_FORUM_PATH_RE = re.compile(
    r"/forums?(?:/|$)|/community(?:/|$)|/boards?(?:/|$)|/discussions?(?:/|$)"
    r"|viewtopic|showthread|viewforum|/threads/|/r/|phpbb|/index\.php\?board="
)

# 'forum'/'forums' inside the registrable label (minecraftforum, linuxforums,
# adamsforums, mineralrightsforum). Content mills don't brand themselves
# 'forum' (they use answers/tips/facts), so this stays high-precision.
_FORUM_DOMAIN_TOKEN_RE = re.compile(r"forum")


def _is_structural_genuine(registered_label: str, subdomains: list[str], path: str) -> bool:
    if any(lbl in _FORUM_SUBDOMAIN_LABELS for lbl in subdomains):
        return True
    if _FORUM_DOMAIN_TOKEN_RE.search(registered_label):
        return True
    if path and _FORUM_PATH_RE.search(path):
        return True
    return False


# ---------------------------------------------------------------------------
# Layer 5 -- non-UGC buckets (best-effort, NOT precision-tuned; see module docstring)
# ---------------------------------------------------------------------------

_SAAS_REGISTERED = {
    "grammarly", "toptal", "kajabi", "clickfunnels", "kartra", "teachable",
    "thinkific", "zendesk", "hubspot", "salesforce", "mailchimp", "wix",
    "squarespace", "godaddy", "bigcartel", "calendly", "notion", "airtable",
    "slack", "zoom", "asana", "trello", "intercom", "freshdesk", "clickup",
    "semrush", "ahrefs", "canva", "figma", "loom", "typeform", "surveymonkey",
    "docusign", "signnow", "dochub", "pandadoc", "pdffiller", "smartsheet",
    "stitcher", "userpilot", "loganix",
}

_EDITORIAL_REGISTERED = {
    # tech media / gadget reviews
    "techradar", "cnet", "tomsguide", "tomshardware", "pcmag", "pcworld",
    "macworld", "theverge", "engadget", "gizmodo", "techcrunch", "zdnet",
    "digitaltrends", "androidauthority", "androidcentral", "anandtech",
    "tweaktown", "makeuseof", "lifehacker", "howtogeek", "pocket-lint",
    "trustedreviews", "techadvisor", "laptopmag", "gsmarena", "phonearena",
    "mashable", "wired", "arstechnica", "bgr", "slashgear", "the-gadgeteer",
    "imore", "idownloadblog", "pcadvisor", "goodgearguide", "techworld",
    "arnnet", "techbullion", "droidrant", "tipsclear", "techhive", "scworld",
    "digitalcameraworld", "techworld", "appleinsider", "9to5mac", "9to5google",
    "pcgamer", "kotaku", "polygon", "ign", "gamespot", "drippler",
    # news / general
    "theguardian", "forbes", "businessinsider", "bloomberg", "reuters",
    "latimes", "chicagotribune", "npr", "nbcnews", "foxbusiness", "foxnews",
    "mercurynews", "azcentral", "dailymail", "thesun", "thescottishsun",
    "montrealgazette", "csmonitor", "japantimes", "sfchronicle", "huffpost",
    "huffingtonpost", "entrepreneur", "icrowdnewswire", "ipsnews", "theregister",
    "bleacherreport", "thesportsdaily", "pasadenastarnews", "staugustine",
    "citizen", "sookenewsmirror", "abc7ny", "fox4now", "thestreet", "cnn",
    "thetimes", "telegraph", "independent", "usatoday", "nypost", "newsweek",
    "time", "vox", "slate", "theatlantic", "axios", "qz",
    # reviews / lifestyle / how-to editorial (independent, not UGC, not mills)
    "seriouseats", "thekitchn", "bonappetit", "allrecipes", "goodhousekeeping",
    "bobvila", "thisoldhouse", "homesandgardens", "thespruce", "wirecutter",
    "consumerreports", "glamour", "seventeen", "stylecraze", "naturallycurly",
    "webmd", "healthline", "mayoclinic", "vetstreet", "autoguide", "moz",
    "bankrate", "nerdwallet", "thesimpledollar", "moneypit", "investopedia",
    "techopedia", "homedit", "thekrazycouponlady", "trustedreviews",
    "sleepopolis", "vintageguitar", "roughguides", "finder", "fixr",
    "lifewire", "thespruceeats", "mentalfloss", "howstuffworks", "verywellhealth",
    "moneyrates", "thoughtco", "treehugger", "byrdie", "realsimple",
}

_COMMERCIAL_REGISTERED = {
    "alibaba", "aliexpress", "made-in-china", "dhgate", "everychina", "diytrade",
    "amazon", "ebay", "etsy", "walmart", "target", "overstock", "barnesandnoble",
    "bestbuy", "wayfair", "wish", "newegg", "bigcommerce", "woocommerce",
    "lazada", "shopee", "flipkart", "ubuy", "desertcart", "etoren", "kikitop",
    "banggood", "gearbest", "rakuten", "bonanza", "poshmark", "mercari", "depop",
    "luckyvitamin", "holabirdsports", "performbetter", "ajmadison", "boattrader",
    "shopify",  # storefront platform; treat hosted stores as commercial
}

# subdomain prefixes / suffix tokens that indicate a storefront
_STORE_SUFFIX_RE = re.compile(r"(?:store|shop|shoppe|outlet|mall|bazaar|mart|kart)$")
_STORE_PREFIX_RE = re.compile(r"^(?:shop|store|buy|order)")
_STORE_SUBDOMAINS = {"shop", "store", "stores", "shopping", "checkout", "cart"}
_SUPPORT_SUBDOMAINS = {"help", "support", "docs", "kb", "developer", "dev", "api"}


def _classify_non_ugc(host, registered_label, etld1, suffix, subdomains, path) -> str:
    if registered_label in _SAAS_REGISTERED:
        return "saas_product"
    if registered_label in _EDITORIAL_REGISTERED:
        return "editorial_review"
    if registered_label in _COMMERCIAL_REGISTERED:
        return "commercial_store"
    # *.myshopify.com style hosted stores
    if etld1.endswith("myshopify.com") or registered_label == "myshopify":
        return "commercial_store"
    # *.zendesk.com / *.clickfunnels.com hosted SaaS instances
    if registered_label in {"zendesk", "clickfunnels", "kajabi", "mystrikingly",
                            "webflow", "weebly", "blogspot", "wordpress"} and subdomains:
        return "saas_product" if registered_label in {"zendesk", "clickfunnels"} else "brand_marketing"
    # storefront-shaped names
    if (any(sd in _STORE_SUBDOMAINS for sd in subdomains)
            or _STORE_SUFFIX_RE.search(registered_label)
            or _STORE_PREFIX_RE.search(registered_label)):
        return "commercial_store"
    # support/docs subdomains on an otherwise unknown product => brand
    if any(sd in _SUPPORT_SUBDOMAINS for sd in subdomains):
        return "brand_marketing"
    return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_host(host: str) -> str:
    """Classify a host into one of CATEGORIES.

    Accepts a bare host (``forum.arduino.cc``) or a full URL; for a URL the
    path is used only to fire forum-path signals.
    """
    if not host or not isinstance(host, str):
        return "unknown"
    h, path = _strip_to_host(host)
    if not h or "." not in h:
        return "unknown"
    registered_label, etld1, suffix, subdomains = _split_host(h)

    # 1. spam / junk first -- a forum word must never rescue free-TLD junk
    if _is_spam(h, registered_label, suffix, subdomains):
        return "spam_low_quality"

    # 2. curated genuine platforms (trusted; beat SEO + structural heuristics)
    if _is_curated_genuine(h, registered_label, etld1, subdomains):
        return "genuine_ugc"

    # 3. SEO content farms BEFORE structural genuine, so 'howtodiscuss' etc.
    #    cannot be admitted by the 'discuss'/'board' structural rule.
    if _is_seo_farm(registered_label):
        return "seo_content_farm"

    # 4. high-precision structural forum/community signals
    if _is_structural_genuine(registered_label, subdomains, path):
        return "genuine_ugc"

    # 5. best-effort non-UGC buckets (not precision-tuned)
    return _classify_non_ugc(h, registered_label, etld1, suffix, subdomains, path)


def is_genuine_ugc(host: str) -> bool:
    """True only for genuine forum / Q&A / community / discussion hosts."""
    return classify_host(host) == "genuine_ugc"


# ---------------------------------------------------------------------------
# Smoke test for the labelled examples in the spec.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    must_genuine = [
        "reddit.com", "ask.metafilter.com", "stackoverflow.com",
        "photo.stackexchange.com", "minecraftforum.net", "linuxforums.org",
        "forum.arduino.cc", "community.giffgaff.com", "houzz.com", "quora.com",
        "tripadvisor.com",
    ]
    must_seo = [
        "psichologyanswers.com", "sage-answers.com", "answers.college",
        "seniorcare2share.com", "howtodiscuss.com", "howto.org", "how.co",
        "moviecultists.com", "remodelormove.com", "easierwithpractice.com",
    ]
    must_spam = ["hack-forum.ml", "entropiaforum.gq", "forumtestxv-01.xooit.fr"]
    must_not_genuine = must_seo + must_spam + [
        "airsoftstation.com", "grammarly.com", "toptal.com", "kajabi.com",
    ]

    ok = True
    for hh in must_genuine:
        got = classify_host(hh)
        flag = "OK " if got == "genuine_ugc" else "FAIL"
        if got != "genuine_ugc":
            ok = False
        print(f"[{flag}] genuine_ugc  {hh:32s} -> {got}")
    for hh in must_seo:
        got = classify_host(hh)
        flag = "OK " if got == "seo_content_farm" else "FAIL"
        if got != "seo_content_farm":
            ok = False
        print(f"[{flag}] seo_farm      {hh:32s} -> {got}")
    for hh in must_spam:
        got = classify_host(hh)
        flag = "OK " if got == "spam_low_quality" else "FAIL"
        if got != "spam_low_quality":
            ok = False
        print(f"[{flag}] spam          {hh:32s} -> {got}")
    for hh in must_not_genuine:
        if is_genuine_ugc(hh):
            ok = False
            print(f"[FAIL] must NOT be genuine: {hh}")
    print("\nALL EXAMPLES PASS" if ok else "\nSOME EXAMPLES FAILED")
