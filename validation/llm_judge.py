#!/usr/bin/env python3
"""Blind LLM third rater: labels each item's authenticity + provenance independently, seeing the same
material a human sees (question + host + URL + the cue/class definitions). It never reads human labels and
is never shown to annotators; its output is a disclosed cross-check + triage signal, not ground truth.
Uses Gemini, a model family independent of the classifiers in this repo (a cleaner third rater).

Input:  $WORKDIR/validation_sample.csv (item_id,dump,era,question,host,url,pclass)
Output: $WORKDIR/llm_labels.csv (item_id,llm_authenticity,llm_provenance) with the model id in a header comment.

Requires: `pip install google-genai` and GEMINI_API_KEY.
Model via $LLM_JUDGE_MODEL (default gemini-3.5-flash; pin the exact id you run --- the output header
records model id + run date for disclosure). $LIMIT>0 processes only the first N items (smoke test).
"""
import os, sys, csv, json, time, re, datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKDIR = os.environ.get("WORKDIR", "/tmp/validation_work")
MODEL = os.environ.get("LLM_JUDGE_MODEL", "gemini-3.5-flash")  # GA; API offers no frozen text snapshot
# (gemini-2.0-flash-*-001 are deprecated/404), so we record the id + run date for disclosure instead.
LIMIT = int(os.environ.get("LIMIT", "0"))
OUT = os.path.join(WORKDIR, "llm_labels.csv")

SYSTEM = (
    "You independently classify a web question. Judge from the question text, its host/URL, and the page's "
    "as-crawled text (if provided) — the same material the human raters saw.\n"
    "AUTHENTICITY — decide via three cues: community (is the HOST a person-to-person community where readers "
    "post to each other: forum/comments/Q&A/mailing list? interviews, blogs, editorials and articles are NOT), "
    "templated (canonical/boilerplate/SEO/FAQ, one-of-a-list? a bespoke editorial/interview question is NOT), "
    "personal (first-person/situated?). Then label:\n"
    "  genuine = (community OR personal) AND NOT templated; manufactured = templated; unclear = otherwise "
    "(including bespoke editorial/interview text with no personal or community signal).\n"
    "PROVENANCE (host-type): genuine-UGC | manufactured-template | commerce-faq | editorial | unknown.\n"
    'Respond ONLY with compact JSON: {"authenticity": "...", "provenance": "..."}.'
)
AUTH = {"genuine", "manufactured", "unclear"}
PROV = {"genuine-UGC", "manufactured-template", "commerce-faq", "editorial", "unknown"}


def _load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    _load_env()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        sys.exit("set GEMINI_API_KEY to run the LLM judge.")
    from google import genai
    from google.genai import types
    client = genai.Client()
    # Gemini 2.5 spends output tokens on "thinking"; disable it + give headroom so JSON actually returns.
    try:
        cfg = types.GenerateContentConfig(system_instruction=SYSTEM, max_output_tokens=256, temperature=0,
                                          thinking_config=types.ThinkingConfig(thinking_budget=0))
    except Exception:
        cfg = types.GenerateContentConfig(system_instruction=SYSTEM, max_output_tokens=256, temperature=0)

    csv.field_size_limit(10_000_000)
    rows = list(csv.DictReader(open(os.path.join(WORKDIR, "validation_sample.csv"))))
    if LIMIT:
        rows = rows[:LIMIT]
    content = {}
    cpath = os.path.join(WORKDIR, "content.csv")
    if os.path.exists(cpath):
        content = {r["item_id"]: (r.get("snippet", "") or "") for r in csv.DictReader(open(cpath))}
    done = {}
    if os.path.exists(OUT):
        done = {r["item_id"]: r for r in csv.DictReader(l for l in open(OUT) if not l.startswith("#"))}

    with open(OUT, "w", newline="") as f:
        f.write(f"# blind LLM third rater; model={MODEL}; run={datetime.date.today().isoformat()}\n")
        w = csv.DictWriter(f, fieldnames=["item_id", "llm_authenticity", "llm_provenance"])
        w.writeheader()
        n_ok = 0
        for r in rows:
            iid = r["item_id"]
            if iid in done and done[iid].get("llm_authenticity"):
                w.writerow({k: done[iid][k] for k in w.fieldnames}); n_ok += 1; continue
            user = f"Question: {r['question']}\nHost: {r['host']}\nURL: {r['url']}"
            if content.get(iid):
                user += f"\nPage as crawled: {content[iid][:2500]}"
            auth = prov = ""
            for attempt in range(3):
                try:
                    resp = client.models.generate_content(model=MODEL, contents=user, config=cfg)
                    txt = resp.text or ""
                    m = re.search(r"\{.*\}", txt, re.S)
                    if not m:
                        raise ValueError(f"no JSON in response: {txt[:80]!r}")
                    obj = json.loads(m.group(0))
                    a, p = obj.get("authenticity", ""), obj.get("provenance", "")
                    if a in AUTH and p in PROV:
                        auth, prov = a, p; break
                except Exception as e:
                    if attempt == 2:
                        print(f"WARN {iid}: {e}", file=sys.stderr)
                    time.sleep(2 * (attempt + 1))
            w.writerow({"item_id": iid, "llm_authenticity": auth, "llm_provenance": prov})
            f.flush()
            if auth:
                n_ok += 1
    print(f"wrote {OUT} (model={MODEL}); labeled {n_ok}/{len(rows)}")


if __name__ == "__main__":
    main()
