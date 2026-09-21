# You Can Tell Who's Asking

**What the Web's Questions Are Made Of, and Where They Come From**
Calvin Zhou, Vincent McCloskey, Krishna Srinivasan
WaC-13, EMNLP 2026

Code and data for the paper.

## Contents

| Path | |
|---|---|
| `validation/` | 150-item validation sample, rubric, annotation tool, LLM-judge script |
| `form/` | form classifier |
| `context/` | context classifier |
| `classifiers/` | UGC host classifier, site-type labeler, host seeds |
| `data/` | per-figure curves and robustness results |
| `data/SAMPLING.md` | how to rebuild the 2.2M question sample |

## Data

| File | |
|---|---|
| `curves_110.csv` | intensity, duplication (D≥2/5/10), forum-host shares |
| `provenance_over_time.csv` | the five provenance classes |
| `absolute_rate.csv` | each class as a rate per page |
| `per_snapshot_denominators.csv` | occurrences and question-bearing pages |
| `fixed_host_panel.csv` | hosts present in ≥90% of snapshots |
| `size_sensitivity.csv` | curves adjusted for crawl size |
| `residual_reassignment.csv` | genuine share under reassignment of the unknown residual |
| `multiple_comparisons.csv` | Benjamini-Hochberg across reported trends |
| `regex_sensitivity.csv` | host-type shares without the collision-prone patterns |
| `concentration.csv`, `context_curves.csv`, `context_by_provenance.csv`, `form_over_time.csv`, `head_composition.csv` | remaining figure series |

## Provenance cascade

First match wins:

1. UGC host or person-to-person URL pattern → `genuine-UGC`
2. normalized text on ≥2 registrable domains → `manufactured-template`
3. commerce or support/FAQ host → `commerce-faq`
4. news, blog or media host → `editorial`
5. otherwise → `unknown`

`classifiers/forum_host_classifier.py` decides step 1: deterministic patterns over host strings, no training
data, precision-first, `unknown` by default. `host_labeler.py` and `host_seeds.csv` decide steps 3-4.

## Withheld

Host, URL and page text are not released, and annotators are anonymized a1/a2/a3. `annotator.html` and
`llm_judge.py` read those fields, so they show how labels were made but won't re-run on `annotations.csv`.
Per-occurrence question text is not released; see `data/SAMPLING.md`.

## Tests

`python -m pytest`. Needs `spacy` and `en_core_web_sm` (`form/requirements.txt`).

## Citation

```bibtex
@inproceedings{zhou2026whosasking,
  title     = {You Can Tell Who's Asking: What the Web's Questions Are Made Of, and Where They Come From},
  author    = {Zhou, Calvin and McCloskey, Vincent and Srinivasan, Krishna},
  booktitle = {Proceedings of the 13th Web as Corpus Workshop (WaC-13)},
  year      = {2026}
}
```

<!-- TODO: ACL Anthology id, pages, url -->

## License

See `LICENSE`. Corpus is Common Crawl via FineWeb, ODC-By.
