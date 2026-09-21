"""Site-type host labeler (PROVENANCE_SPEC §3). Host-type provenance, where a question lives, NOT
question commercial-intent (that is the reserved enrichment taxonomy). Deterministic seed-lookup + era-neutral
regex heuristics; interpretable and releasable. Categories: commerce, editorial, faq, ugc, other."""
import re

# Curated known-brand substrings (checked before the generic heuristics), famous hosts that lack the
# keyword substrings the heuristics rely on. Genuine-UGC is handled separately by the UGC host
# classifier, so this map covers only commerce / editorial / faq.
_CURATED = [
    ("editorial", ("nytimes", "cnn.", "cnn.com", "bbc.", "theguardian", "guardian.", "washingtonpost",
                   "huffingtonpost", "huffpost", "forbes", "reuters", "nbcnews", "abcnews", "cbsnews",
                   "foxnews", "npr.org", "slate.com", "theatlantic", "vox.com", "buzzfeed", "businessinsider",
                   "bloomberg", "wsj.com", "usatoday", "telegraph", "dailymail", "independent.co", "time.com",
                   "newsweek", "politico", "vice.com", "salon.com", "glamour", "vogue", "hollywoodlife",
                   "variety", "wired.com", "techcrunch", "engadget", "gizmodo", "mashable", "medium.com",
                   "wordpress", "blogspot", "tumblr", "substack", "bleacherreport", "theverge", "cnbc",
                   "aljazeera", "economist", "fool.com", "patheos", "hollywood")),
    ("commerce",  ("amazon.", "ebay.", "etsy.", "walmart", "target.com", "bestbuy", "alibaba", "aliexpress",
                   "shopify", "wayfair", "homedepot", "lowes.com", "macys", "costco", "ikea.", "overstock",
                   "newegg", "zappos", "wish.com", "groupon", "craigslist")),
    ("faq",       ("zendesk", "support.", "help.", "faq.", "answers.microsoft", "docs.")),
]

# Generic heuristics (first match wins). UGC first so a "news forum" reads as UGC.
_RULES = [
    ("ugc",       re.compile(r"(forum|community|discuss|board|reddit)", re.I)),
    ("commerce",  re.compile(r"(shop|store|cart|buy|deals|coupon|pricing|ecommerce)", re.I)),
    ("editorial", re.compile(r"(news|blog|magazine|times|post|herald|journal|media|wire)", re.I)),
    ("faq",       re.compile(r"(support|help|faq|docs|kb|answers|knowledgebase)", re.I)),
]


def label(host, seed=None):
    """Return the site-type category for a host string. `seed` (host->category) wins over everything;
    then a curated known-brand map; then generic regex heuristics; else 'other'."""
    if not host:
        return "other"
    if seed and host in seed:
        return seed[host]
    h = host.lower()
    for cat, subs in _CURATED:
        if any(s in h for s in subs):
            return cat
    for cat, rx in _RULES:
        if rx.search(host):
            return cat
    return "other"
