# Context-independence rubric

Deterministic three-way label per question, **first match wins** (strict priority 1 > 2 > 3).
Engine: `form.pos_adapter.analyze_batch` (`en_core_web_sm` with
tagger + attribute_ruler; **parser/ner/lemmatizer excluded**: so only POS/tag/text/position are
available, no dependency labels and no lemmas). Rules are therefore **POS-based**.

Token fields available per token: `text`, `lower`, `tag` (PTB), `pos` (UD coarse), `is_punct`, `i`.

## 1. conversational-fragment: "someone mid-conversation"
- contains 2nd-person deixis: any token whose `lower` ∈ {`you`, `your`, `yours`}; **OR**
- opens with a discourse marker + comma: token[0]`.lower` ∈ {`so`, `and`, `but`, `ok`, `okay`,
  `well`} **and** token[1]`.text` == `,`.

## 2. context-dependent: unresolved reference to something outside the question
- **dangling demonstrative:** a token with `lower` ∈ {`this`, `that`, `these`, `those`} and
  `pos` ∈ {`DET`, `PRON`} that has **no following head noun**: scanning forward, skipping
  `DET`/`ADJ`/`NUM`/`ADV`, the next content token is not `NOUN`/`PROPN` (so "is *this* covered",
  "how do I fix *that*" fire; "*this* book", "*this* good idea" do not, since they have a head noun).
  This is the POS-only proxy for "demonstrative without an in-question antecedent NP". Complementizer
  "that" (`pos` == `SCONJ`) is excluded by the POS gate.
- **anaphoric "it":** a token `lower` == `it`, `pos` == `PRON`, with **no** `NOUN`/`PROPN` token
  before it in the question (no in-question antecedent). *Known limitation: expletive "it" ("is it
  true that…") is counted here, quantified by the 100-item validation, not corrected in-rule.*
- **definite reference to an unstated artifact:** the question contains the token sequence
  `the above` or `the following`, or the token `either` (`lower` match). (Token-level equivalent of
  `\b(the above|the following|either)\b`.)

## 3. self-contained: none of the above.

Deterministic; no randomness, no thresholds. See `context/context_classifier.py` (the implementation
is the single source of truth for edge cases) and `context/tests/test_context_classifier.py`.
