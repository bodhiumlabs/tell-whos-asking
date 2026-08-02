"""Deterministic context-independence rubric (context/RUBRIC.md). Priority 1 > 2 > 3.

POS-based only: `form.pos_adapter` excludes the parser/lemmatizer, so rules use
token text/lower/pos/position, with no dependency labels and no lemmas.
"""
from form.pos_adapter import analyze_batch

SECOND = {"you", "your", "yours"}
DISCOURSE = {"so", "and", "but", "ok", "okay", "well"}
DEMS = {"this", "that", "these", "those"}
_SKIP = {"DET", "ADJ", "NUM", "ADV"}          # modifiers between a determiner and its head noun
_HEAD = {"NOUN", "PROPN"}


def _has_head_noun(toks, i):
    """True if a NOUN/PROPN head follows token i, skipping only DET/ADJ/NUM/ADV modifiers."""
    for t in toks[i + 1:]:
        if t["pos"] in _SKIP:
            continue
        return t["pos"] in _HEAD
    return False


def classify_context(item):
    """item = one analyze_batch() result dict ({'tokens': [...], ...}) -> label str."""
    toks = item["tokens"]
    low = [t["lower"] for t in toks]

    # 1. conversational-fragment
    if any(w in SECOND for w in low):
        return "conversational-fragment"
    if len(toks) >= 2 and low[0] in DISCOURSE and toks[1]["text"] == ",":
        return "conversational-fragment"

    # 2. context-dependent
    for i, t in enumerate(toks):
        if t["lower"] in DEMS and t["pos"] in ("DET", "PRON") and not _has_head_noun(toks, i):
            return "context-dependent"
    for i, t in enumerate(toks):
        if t["lower"] == "it" and t["pos"] == "PRON":
            if not any(p["pos"] in _HEAD for p in toks[:i]):
                return "context-dependent"
    for i in range(len(low) - 1):
        if low[i] == "the" and low[i + 1] in ("above", "following"):
            return "context-dependent"
    if "either" in low:
        return "context-dependent"

    # 3.
    return "self-contained"


def classify_batch(questions):
    return [classify_context(item) for item in analyze_batch(questions)]
