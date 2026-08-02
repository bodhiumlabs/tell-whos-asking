# tell-whos-asking

Artifacts for *Who's Asking?*

| Contents | Path |
|---|---|
| Validation sample, 150 items labelled by 3 annotators | `validation/annotations.csv` |
| Annotation rubric and the tool annotators worked in | `validation/guidelines.md`, `validation/annotator.html` |
| Blind LLM-judge script (prompt, model id, decoding settings) | `validation/llm_judge.py` |
| Form classifier | `form/` |
| Context classifier | `context/` |
| Per-figure curve data | `data/` |

Host, URL, and page text are withheld from the released sample, and annotators are anonymized as
a1, a2, a3. `annotator.html` and `llm_judge.py` read those withheld fields, so both ship to show how
the labels were produced, not as something re-runnable on `annotations.csv`.

Tests: `python -m pytest` from the repo root. Needs `spacy` and `en_core_web_sm`; see
`form/requirements.txt`.
