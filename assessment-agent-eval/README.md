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

cd assessment-agent-eval
cp .env.example .env        # then paste your Gemini key (free: https://aistudio.google.com/app/apikey)

python run_eval.py --provider mock    # offline smoke test, no key needed
python run_eval.py                    # real run with Gemini (config.yaml default)
```

The editable install (`-e`) is what makes `import agents` work from here without
any `sys.path` juggling — and it means the eval measures the *same* agent code the
backend will import, not a copy of it.

The report lands in `reports/<timestamp>_<promptversion>.html`. Open it in a browser.

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

   The rubric and example set are a **matched pair** — a rubric change that
   renames/removes/redefines criteria needs a matching example-set bump. Then point
   `config.yaml` (`prompt_version` / `rubric_version` / `example_set_version`) at the
   versions you want. Each run stamps all three (+ a composed prompt+rubric hash)
   into the report and `results_log.csv`.
4. Re-run, compare, and log the effect in `CHANGELOG.md`.
5. Repeat until the (TBD) per-step accuracy threshold is met.

`python run_eval.py --from-run runs/<dir>` rebuilds a report from saved raw outputs
without spending any API calls.

## Ground truth (note for adviser review)

The active `v2` example set (`data/example_set_v2.csv`) is a fresh, hand-written set
of **18 examples** — 8 PASS controls + 10 of the most likely natural mistakes —
covering all 13 rubric criteria, each with a `rationale` column explaining its
expected label. Like the `v2` rubric, it should be confirmed by Dr. Teehankee before
being treated as final ground truth.

The earlier `v1` set is preserved as `data/example_set_v1.csv` (its matched rubric is
`agents/rubrics/rubric_v1.yaml`) so the 2026-06-19 baseline run stays reproducible.

## Layout

```
SENSEEI/
├─ pyproject.toml            installs the `agents` package: pip install -e ".[gemini]"
├─ agents/                   THE AGENT — shared with the future backend
│  ├─ assessment.py          prompt assembly + JSON parse/validate + verdict derivation
│  ├─ rubric.py              loads the rubric YAML; criterion names + prompt rendering
│  ├─ providers/             gemini / openai_compat / mock
│  ├─ prompts/               versioned system prompts (system_prompt_vN.md; {{RUBRIC}} slot)
│  └─ rubrics/               versioned rubric — single source of truth (rubric_vN.yaml)
└─ assessment-agent-eval/    THE HARNESS — measures the agent above
   ├─ run_eval.py            entry point
   ├─ config.yaml            provider/model + pinned input versions (eval runs only)
   ├─ .env.example           API keys (copy to .env)
   ├─ data/
   │  ├─ example_set_vN.csv  labeled examples (matched to a rubric version)
   │  └─ readings/*.txt      the source texts the examples respond to
   ├─ src/
   │  ├─ compare.py          expected-vs-actual + stats
   │  └─ report.py           HTML rendering
   ├─ runs/                  raw JSON per run (reproducibility cache)
   ├─ reports/               timestamped HTML reports
   ├─ results_log.csv        per-run summary metrics
   └─ CHANGELOG.md           per-iteration notes
```

The split is the point: everything under `agents/` ships, everything under
`assessment-agent-eval/` only measures.
