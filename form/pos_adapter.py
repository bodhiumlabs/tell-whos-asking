"""Thin POS/tokenization adapter. Isolates the NLP engine (spaCy) behind a plain-dict interface so the
rule layer never imports spaCy directly and the engine can be swapped without touching the rules."""
import spacy

_NLP = None
FINITE_TAGS = {"VBZ", "VBP", "VBD", "MD"}          # tensed/modal verbs (finite)
WH_TAGS = {"WP", "WP$", "WRB", "WDT"}              # interrogative wh-words


def _nlp():
    global _NLP
    if _NLP is None:
        # The rules use only POS tags (tagger + attribute_ruler) and sentence counts. The dependency
        # parse, NER, and lemmatizer are unused, so exclude them and add the fast rule-based sentencizer
        # ~10-20x faster over millions of questions, with identical tags.
        _NLP = spacy.load("en_core_web_sm", exclude=["parser", "ner", "lemmatizer"])
        if "sentencizer" not in _NLP.pipe_names:
            _NLP.add_pipe("sentencizer")
    return _NLP


def _to_analysis(doc):
    tokens = [{"text": t.text, "lower": t.lower_, "tag": t.tag_, "pos": t.pos_,
               "is_punct": t.is_punct, "i": t.i} for t in doc]
    return {"tokens": tokens, "n_sents": max(1, len(list(doc.sents)))}


def analyze(text):
    return _to_analysis(_nlp()(text))


def analyze_batch(texts, batch_size=512):
    """Batched analysis via nlp.pipe, the fast path for classifying many questions."""
    for doc in _nlp().pipe(texts, batch_size=batch_size):
        yield _to_analysis(doc)
