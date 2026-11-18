# SENSEEI — Student Assessment Agent: Evaluation Harness

Self-contained testbed for iteratively developing the **Student Assessment Agent**
(the SEE-I pass/fail grader) *in isolation* — not the full multi-agent pipeline.

It takes a CSV of labeled examples, runs each through the agent (one LLM call with
the system prompt under test), and produces an HTML report comparing the agent's
verdict + failing criteria against the expected labels.

## Quick start

```bash
# from the REPO ROOT — the agent itself lives in the shared `agents` package
python -m venv .venv && .venv\Scripts\activate     # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -e ".[gemini]"            # use ".[openai]" instead for the openai_compat provider

cp .env.example .env        # then paste your Gemini key (free: https://aistudio.google.com/app/apikey)

cd assessment-agent-eval

python run_eval.py --provider mock    # offline smoke test, no key needed
python run_eval.py                    # real run with Gemini (config.yaml default)
```

The editable install (`-e`) is what makes `import agents` work from here without
any `sys.path` juggling — and it means the eval measures the *same* agent code the
backend will import, not a copy of it.

The report lands in `reports/<timestamp>_<promptversion>.html`. Open it in a browser.

### Common commands

All from `assessment-agent-eval/`. Explicit paths are relative to this folder.

| What | Command |
| --- | --- |
| Offline smoke test (no key, no cost) | `python run_eval.py --provider mock` |
| Real run with the versions pinned in `config.yaml` | `python run_eval.py` |
| Quick check on the first few rows | `python run_eval.py --limit 3` |
| Run the human-annotated set (see [Example sets v4 and v5](#example-sets-v4-and-v5-human-annotated)) | `python run_eval.py --csv data/example_set_v5.csv` |
| Try a prompt without pinning it | `python run_eval.py --prompt ../agents/prompts/system_prompt_v4.md` |
| Try a rubric without pinning it | `python run_eval.py --rubric ../agents/rubrics/rubric_v4.yaml` |
| Another model | `python run_eval.py --model <model-id>` |
| Rebuild a report, no API calls | `python run_eval.py --from-run runs/<dir>` |
| Edit and compare prompts and rubrics | `python serve.py` (see [Prompt editor](#prompt-editor-local)) |

Flags combine, e.g. `python run_eval.py --csv data/example_set_v5.csv --limit 3`. Every run, the
mock included, adds a folder under `runs/`, a report under `reports/` and a row in
`results_log.csv`.
Calls are spaced to `requests_per_minute` in `config.yaml` (15), so 69 responses take about
5 minutes.

## How it works

```
data/example_set_vN.csv       ─┐
data/readings/*.txt           ─┤
agents/rubrics/rubric_vN.yaml ─┼─► run_eval.py ─► AssessmentAgent ─► provider (LLM) ─► JSON
agents/prompts/system_*.md    ─┘         │        (rubric rendered into the prompt's {{RUBRIC}} slot)
                                         ├─► compare vs expected labels
                                         ├─► runs/<ts>/results.json   (raw outputs, cached)
                                         ├─► reports/<ts>_<ver>.html  (the review artifact)
                                         └─► results_log.csv          (one row per run, for charting)
```

The top two inputs are the eval's own; the bottom two, and the agent itself, come
from the shared `agents/` package at the repo root.

The agent checks **every** rubric row for the current step and collects **all**
failing criteria (it does not stop at the first failure), per the project spec. The
overall verdict is then **derived in code** (any failing criterion → FAIL); the
model's own stated verdict is kept only as a self-consistency cross-check.

## Swapping the LLM provider

Everything is config-driven (`config.yaml` + `.env`) — no code changes to switch:

| Provider | `provider:` | Notes |
|---|---|---|
| Google Gemini (default) | `gemini` | Free tier, native JSON output |
| Groq / OpenRouter / Together / Ollama / OpenAI | `openai_compat` | set `base_url`, `model`, `api_key_env` |
| Offline stub | `mock` | always returns PASS — pipeline smoke test only |

To add a brand-new backend: implement `complete()` in `agents/providers/` and register
it in `agents/providers/__init__.py`. For the real SENSEEI app, point `openai_compat`
(or a new adapter) at your paid SOTA model.

## Output format

The agent returns JSON like:

```json
{
  "verdict": "FAIL",
  "fail_criteria": ["Clarity", "Accuracy"],
  "criteria": { "Clarity": {"pass": false, "reason": "starts with 'It'"}, ... },
  "raw_response": "one-sentence justification"
}
```

`criteria` (per-row reasoning) is included so you can see *why* the agent ruled each
rubric criterion — invaluable when tuning the prompt. The harness **derives** the
scored verdict from `criteria` (any `pass: false` → FAIL); the model's `verdict`
field is recorded only to flag self-contradiction. Parsing is defensive
(`agents/assessment.py`): it strips code fences, normalizes criterion names, and records
warnings (hallucinated criteria, missing criteria, verdict/criteria mismatches)
instead of crashing.

## Reading the report

- **Per-example rows**, color-coded: green = verdict + criteria agree, amber =
  verdict agrees but criteria differ, red = verdict mismatch, gray = parse error.
- **Criteria diff** column: ✓ matched, ✗ missed (expected but not flagged),
  + extra (flagged but not expected).
- **Top cards + per-step table**: overall and per-SEE-I-step verdict accuracy
  (supports a per-step exit threshold later).
- **Per-criterion catch-rate table**: how reliably each criterion is caught — tells
  you which rubric row to target in the next prompt revision.

## Iteration workflow

1. Run the set, open the report.
2. Find the weakest criterion / step in the catch-rate table.
3. Change **one thing**, as a new version (old versions are never overwritten):
   - prompt wording → copy `agents/prompts/system_prompt_vN.md` → next N
   - rubric → copy `agents/rubrics/rubric_vN.yaml` → next N
   - examples → copy `data/example_set_vN.csv` → next N

   The [prompt editor](#prompt-editor-local) does the first two for you.

   The rubric and example set are a **matched pair** — a rubric change that
   renames/removes/redefines criteria needs a matching example-set bump. Then point
   `config.yaml` (`prompt_version` / `rubric_version` / `example_set_version`) at the
   versions you want. Each run stamps all three (+ a composed prompt+rubric hash)
   into the report and `results_log.csv`.
4. Re-run, compare, and log the effect in `CHANGELOG.md`.
5. Repeat until the (TBD) per-step accuracy threshold is met.

`python run_eval.py --from-run runs/<dir>` rebuilds a report from saved raw outputs
without spending any API calls.

## Prompt editor (local)

```bash
python serve.py        # opens http://127.0.0.1:8765; Ctrl+C to stop
```

A small local page for step 3 above. Pick a version to start from, edit the Assessment Agent's
system prompt or the rubric, and **Save** writes the next number
(`agents/prompts/system_prompt_v5.md`, `agents/rubrics/rubric_v5.yaml`) and adds a line to
`versions.csv` beside it (version, based on, time, your note). It never overwrites an existing
version, refuses a save with no changes, and numbers prompts and rubrics separately. The tutor and
figure prompts in the same folder are left alone.

Saving changes nothing that runs. The eval keeps using what `config.yaml` pins and the backend
what its settings pin (`assessment_prompt_version`, `rubric_version`); a new version is used only
once someone pins it.

- **Show changes** diffs against the version you started from, with checks: the prompt must keep
  `{{RUBRIC}}` exactly once, and the rubric must be valid YAML with all four steps and a pass
  condition for every criterion. If a criterion that the pinned example set expects to fail is
  renamed or removed, it warns, since those rows could no longer match.
- **Preview what the model sees** fills the rubric into the prompt and shows the hash that
  `results_log.csv` records for a run with it.
- After a save it shows the command to try it without pinning it
  (`python run_eval.py --prompt ../agents/prompts/system_prompt_v5.md`).
- **Compare versions** diffs any two prompts (or rubrics), with changed words highlighted and a
  "show whole file" switch. Each side shows when the version was created (the save log, or for
  older versions the commit that first added the file) and the runs in `results_log.csv` that
  used it. Compare accuracy only between runs on the same model and example set.

It listens on `127.0.0.1` only and refuses requests from other hosts or origins, since it can
write files. It needs nothing beyond the base install; `--port N` and `--no-open` are available.
Its tests need no key or database:

```bash
pip install -e ".[dev]"                 # once, for pytest
pytest assessment-agent-eval/tests      # from the repo root
```

## Ground truth (note for adviser review)

The active `v2` example set (`data/example_set_v2.csv`) is a fresh, hand-written set
of **18 examples** — 8 PASS controls + 10 of the most likely natural mistakes —
covering all 13 rubric criteria, each with a `rationale` column explaining its
expected label. Like the `v2` rubric, it should be confirmed by Dr. Teehankee before
being treated as final ground truth.

The earlier `v1` set is preserved as `data/example_set_v1.csv` (its matched rubric is
`agents/rubrics/rubric_v1.yaml`) so the 2026-06-19 baseline run stays reproducible.

### Example sets v4 and v5 (human-annotated)

Both hold responses labeled by human annotators, one consensus (or adjudicated) pass/fail per
criterion, collapsed to one row per response: `criterion_targeted` lists the criteria the
humans failed and `rationale` their remarks on those criteria. Criterion names match rubrics
`v3` and `v4`.

| Set | Responses | From the annotation export of | Changes |
| --- | --- | --- | --- |
| `example_set_v4.csv` | 69 (47 FAIL, 22 PASS) | 2026-11-02 | first human-annotated set |
| `example_set_v5.csv` | 69 (48 FAIL, 21 PASS) | 2026-11-18 | the same responses as v4; `EX-VIS-OEM` now fails Originality and Explicit Mapping; two remarks cleared |

Use v5 for new runs. v4 is kept so the runs already made on it stay comparable.

Every row reads `data/readings/gamble-ch1-2.txt`, the full text of chapters 1-2 of the
Gamble textbook, as extracted by this app's own upload page (`/library/new`), so the
agent is graded on the text it sees in the app. That file is **git-ignored** because this
repository is public, so a fresh clone does not have it and a v4 or v5 run stops with a
missing-file error until it is added. Get `gamble-ch1-2.txt` from the team and place it at
that path. Do not reconvert the PDF with another tool: a different converter gives
different text, and the results would no longer be comparable.

Each call sends the whole reading (about 26k tokens), so a full run costs roughly $4 at the
Gemini pricing in `config.yaml`, against cents for the short-excerpt sets. Try `--limit 3`
first and check the cost line. To make v5 the default, set `example_set_version: v5` in
`config.yaml`.

## Layout

```
SENSEEI/
├─ pyproject.toml            installs the `agents` package: pip install -e ".[gemini]"
├─ .env.example              API keys, copy to .env (one for the whole repo)
├─ agents/                   THE AGENT — shared with the future backend
│  ├─ assessment.py          prompt assembly + JSON parse/validate + verdict derivation
│  ├─ tutor.py               builds each turn the student reads
│  ├─ rubric.py              loads the rubric YAML; criterion names + prompt rendering
│  ├─ retry.py               provider call with rate-limit backoff, used by both agents
│  ├─ providers/             gemini / openai_compat / mock
│  ├─ prompts/               versioned prompts (system_prompt_vN.md, tutor_prompt_vN.md)
│  └─ rubrics/               versioned rubric — single source of truth (rubric_vN.yaml)
├─ scripts/
│  └─ session.py             play one tutoring session in the terminal
└─ assessment-agent-eval/    THE HARNESS — measures the agent above
   ├─ run_eval.py            entry point
   ├─ serve.py               local prompt/rubric editor (see Prompt editor)
   ├─ config.yaml            provider/model + pinned input versions (eval runs only)
   ├─ data/
   │  ├─ example_set_vN.csv  labeled examples (matched to a rubric version)
   │  └─ readings/*.txt      the source texts the examples respond to
   ├─ src/
   │  ├─ compare.py          expected-vs-actual + stats
   │  ├─ report.py           HTML rendering
   │  ├─ versions.py         editor: versioning, checks, diffs
   │  └─ webui.py            editor: localhost-only JSON API
   ├─ ui/editor.html         the editor page
   ├─ tests/                 editor tests (pytest assessment-agent-eval/tests)
   ├─ runs/                  raw JSON per run (reproducibility cache)
   ├─ reports/               timestamped HTML reports
   ├─ results_log.csv        per-run summary metrics
   └─ CHANGELOG.md           per-iteration notes
```

The split is the point: everything under `agents/` ships, everything under
`assessment-agent-eval/` only measures.
