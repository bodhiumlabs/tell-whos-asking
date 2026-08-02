# Question form typology

The form classifier assigns three independent dimensions to each question. All rules are deterministic
(regex + POS tags), operate on the raw question string, and are documented below.

## 1. Question type: single primary label via a priority cascade (first match wins)

1. **`tag`**: a declarative clause closed by a tag question: `…, isn't it?`, `…, right?`, `…, don't you?`
   (a comma followed by a short tag near the end). Checked first, since it embeds a declarative that would
   otherwise mis-trigger `polar`/`elliptical`.
2. **`imperative-interrogative`**: a verb-initial information request: a clause-leading base-form verb
   (`tell`, `explain`, `list`, `describe`, `name`, `give`, `show`, `compare`, …), not an auxiliary. A leading
   politeness word (`please`) is skipped. Checked before `wh` so "tell me **how** …" is imperative, not wh.
3. **`wh`**: contains an interrogative wh-word (`who what when where why which whose whom how`, POS
   `WP/WP$/WRB/WDT`).
4. **`polar`**: subject–auxiliary inversion at the start, no wh-word: leading `do/does/did/is/are/was/were/
   am/be/can/could/will/would/shall/should/may/might/must`.
5. **`elliptical`**: no finite (tensed/modal) verb, but still a contentful phrase (contains a noun, proper
   noun, or non-finite verb): `best way to lose weight?`, `cheapest flights to New York?`, `side effects of X?`.
   The canonical, headline-style form.
6. **`other`**: none of the above (e.g. a bare number or non-question fragment).

## 2. Person / deixis (priority `first > second > impersonal`)

- **`first`**: contains a first-person pronoun (`i me my mine we us our ours`).
- **`second`**: contains a second-person pronoun (`you your yours`) and no first-person.
- **`impersonal`**: neither (`how to X`, `what is Y`, `how does one Z`).

## 3. Length & scaffolding

- **`n_tokens`**: count of non-punctuation tokens. **`length_bucket`** = `short` (≤6) / `medium` (7–15) /
  `long` (>15).
- **`has_scaffolding`**: true if any of: more than one sentence; a politeness marker
  (`please thanks thank kindly appreciate`); or a leading subordinate/adverbial clause
  (`since because when if after while although though as unless before …`). Distinguishes verbose,
  scaffolded questions from bare canonical ones.

## Output

`classify(question)` returns
`{"type", "person", "n_tokens", "length_bucket", "has_scaffolding"}`.
