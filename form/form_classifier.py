"""Deterministic form-typology classifier. Raw question string in, labels out.
Three independent dimensions: question type (priority cascade), person/deixis, length + scaffolding.
Traditional regex + POS rules only: no ML, no training data, fully interpretable."""
from form.pos_adapter import analyze, FINITE_TAGS, WH_TAGS

AUX = {"be", "is", "are", "was", "were", "am", "do", "does", "did", "have", "has", "had",
       "can", "could", "will", "would", "shall", "should", "may", "might", "must"}
POLITE = {"please", "thanks", "thank", "kindly", "appreciate"}
SUBORD = {"since", "because", "when", "if", "after", "while", "although", "though", "as",
          "unless", "before"}
FIRST = {"i", "me", "my", "mine", "we", "us", "our", "ours"}
SECOND = {"you", "your", "yours", "u", "ur"}
TAG_CUES = {"right", "no", "eh", "okay", "ok"}


def _content(tokens):
    return [t for t in tokens if not t["is_punct"]]


def _is_tag(tokens):
    """Declarative + trailing short tag after a comma: '..., right?' / '..., isn't it?'."""
    commas = [t["i"] for t in tokens if t["text"] == ","]
    if not commas:
        return False
    tail = [t for t in tokens if t["i"] > commas[-1] and not t["is_punct"]]
    if not tail or len(tail) > 3:
        return False
    lows = {t["lower"] for t in tail}
    return bool(lows & TAG_CUES) or any(t["lower"] in AUX for t in tail)


def classify_type(a):
    """Single primary question type via the frozen priority cascade:
    tag -> imperative-interrogative -> wh -> polar -> elliptical -> other."""
    toks = a["tokens"]
    content = _content(toks)
    if not content:
        return "other"
    if _is_tag(toks):
        return "tag"
    # imperative-interrogative: clause-leading base-form verb (skip a leading politeness word), not an aux
    lead = content[0]
    if lead["lower"] in POLITE and len(content) > 1:
        lead = content[1]
    if lead["tag"] == "VB" and lead["lower"] not in AUX:
        return "imperative-interrogative"
    if any(t["tag"] in WH_TAGS for t in toks):
        return "wh"
    if content[0]["lower"] in AUX or content[0]["tag"] == "MD":
        return "polar"
    if not any(t["tag"] in FINITE_TAGS for t in toks):
        # elliptical = no finite verb but still contentful (a noun/verb phrase), not garbage like "42"
        if any(t["pos"] in {"NOUN", "PROPN", "VERB"} for t in content):
            return "elliptical"
    return "other"


def classify_person(a):
    """Person/deixis with priority first > second > impersonal."""
    lows = {t["lower"] for t in a["tokens"]}
    if lows & FIRST:
        return "first"
    if lows & SECOND:
        return "second"
    return "impersonal"


def length_and_scaffold(a):
    """Token count + length bucket + has_scaffolding."""
    content = _content(a["tokens"])
    n = len(content)
    bucket = "short" if n <= 6 else ("medium" if n <= 15 else "long")
    lows = {t["lower"] for t in content}
    polite = bool(lows & POLITE)
    multi = a["n_sents"] > 1
    leading_sub = bool(content) and content[0]["lower"] in SUBORD
    return {"n_tokens": n, "length_bucket": bucket,
            "has_scaffolding": bool(multi or polite or leading_sub)}


def classify(question):
    """Full form-typology label for one raw question string."""
    a = analyze(question or "")
    ls = length_and_scaffold(a)
    return {"type": classify_type(a), "person": classify_person(a),
            "n_tokens": ls["n_tokens"], "length_bucket": ls["length_bucket"],
            "has_scaffolding": ls["has_scaffolding"]}
