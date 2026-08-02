# Annotation rubric: question form & authenticity

The written version of the rubric used for the validation sample. **Annotators worked from
`annotator.html`, not from this file**: the tool carries the same cue and label definitions in its
right-hand panel. This document expands them; the tool is what annotators actually used.

For each web question, decide: **real person asking** (genuine), **produced for a system/business**
(manufactured), or **can't tell** (unclear). Three cues are answered per question, read together with the
page's as-crawled text; authenticity is computed from them. Everything else on the row is a classifier guess
the annotator sanity-checks.

## Protocol

Each annotator labelled ~83 items: a 50-item overlap shared by all three, plus disjoint remainders. The tool
showed, for every question, the **page as it was crawled**, with the question highlighted; judgments were made
from that, not the live URL, since many pages are now dead, parked, or repurposed. **Annotators labelled
independently**, without comparing notes.

## What you fill

Mostly **three characters per row**: the cues:

| cue | ask yourself | answer |
|---|---|---|
| **`c`** community | Is it in a person-to-person space (forum/board, comments, Q&A (reddit, StackExchange), mailing list)? | `y`/`n`/`?` |
| **`t`** templated | Does it read as boilerplate/SEO/FAQ/marketing (canonical, one of a list)? | `y`/`n`/`?` |
| **`p`** personal | First-person or about the asker's own situation ("my 2012 Civic")? | `y`/`n` |

**`t` = the text is a *canned/boilerplate unit***: a FAQ/PAA answer block, an SEO or marketing question, one
of a mass-published list. **Generic wording is NOT templated.** A real person's forum/comment/Q&A post is
`t=n` even when plainly worded. *"How long have you been married?"* on a forum is `t=n` (genuine), not `t=y`.
**Rule of thumb: if `community=y` (a reader posted it), `t` is almost always `n`.** Reserve `t=y` for canned
*page* content (FAQ/PAA/SEO/marketing), never for an ordinary question that merely sounds common. A bespoke
interview, op-ed, or rhetorical question is also `t=n` (→ `unclear`).

- **`auth`: leave blank.** It's computed from your cues; only put `g`/`m`/`u` if the computed label is clearly
  wrong (add a word in `notes`).
- **`provenance` / `type` / `person` / `scaffolding`** come **pre-filled with the classifier's guess,
  overwrite in place only if it's wrong.**
- **`flag` = `u`** if you're genuinely torn.

Valid values, if you need to correct one: `provenance` = genuine-UGC / manufactured-template / commerce-faq /
editorial / unknown · `type` = wh / polar / tag / imperative-interrogative / elliptical / other · `person` =
first / second / impersonal · `scaffolding` = y / n.

## The community cue (the one that trips people up)

Judge **the host, not whether the sentence sounds human.**

- **`c=y`**: forum/board, comment thread, Q&A community, mailing list: readers posting *to each other*.
- **`c=n`**: an interview's questions, a blog **post**, an op-ed, an article: published *at* readers
  (provenance `editorial`), even when a real person is clearly speaking.
- **A site type isn't destiny:** the same blog's **reader comment** is `c=y`. Ask *"author publishing, or
  reader posting?"* → post `c=n`, comment `c=y`.
- **Sanity check:** if `provenance` is `editorial`/`commerce-faq`/`manufactured-template`, `c` is almost always `n`.

**`?`** = you genuinely can't tell **even from the crawled text shown**: use it rather than guess (it feeds
`unclear`). This should be **rare**, since the page text is right there; no need to open the live URL (it may be
dead or repurposed). `p` (personal) has no `?`.

## Examples

- *"Do we need a Living Trust?"* on ask.metafilter.com → `c=y, p=y` → **genuine**.
- *"How do I get wine stains out of a wool rug?"* in a blog **comment** → `c=y, p=y` → **genuine**.
- *"What is a Roth IRA?"*, repeated across finance sites → `t=y` → **manufactured**.
- *"Who is this course for?"* in a course-marketing FAQ → `t=y` → **manufactured**.
- An **interview** or op-ed question → `c=n` (editorial): not a reader asking.
- A law-firm site, neutral question, no clear cue → **unclear** (don't guess).

## Where to spend effort

The cues `c`/`t`/`p` are the product, so give them full care; the crawled text usually makes the venue and intent obvious.
`provenance` rides along: confirm or correct, don't re-deliberate. `scaffolding` and `person` deserve a
2-second check each; `type` just a glance for obvious misroutes. **Don't rubber-stamp the pre-filled labels.**
Target ~45–60 s/item.
