# Rebuilding the 2.2M sample

Form and context are estimated on 20k questions per snapshot (2.2M over 110), not the full population.

## Selection

```sql
MOD(ABS(FARM_FINGERPRINT(question)), K) = 0
```

On the raw question string, per snapshot, with `K` set so the count lands at 20k, drawn from parquet files
spaced across the dump. Deterministic and content-addressed: no seed, no stored row ids.

## Normalization

Counting and duplication use `nq`:

1. NFKC
2. lowercase
3. collapse whitespace, trim
4. strip leading/trailing `' " “ ” ‘ ’ « » ¿ ¡ ? ! . , : ; ( ) [ ] - – —`

No stemming, no fuzzy matching. Cross-host duplication is a lower bound.

## Question definition

A sentence with a question mark, 5-100 words, starting with a question word or containing an interrogative
keyword. The extractor runs upstream and is not in this release.

## Why no document ids

A FineWeb document identifier resolves to the page, and host and URL are withheld. The rule above rebuilds the same sample
from the public corpus.
