# SENSEEI — Student Assessment Agent: Evaluation Harness

Self-contained testbed for iteratively developing the **Student Assessment Agent**
(the SEE-I pass/fail grader) *in isolation* — not the full multi-agent pipeline.

It takes a CSV of labeled examples, runs each through the agent (one LLM call with
the system prompt under test), and produces an HTML report comparing the agent's
verdict + failing criteria against the expected labels.

## Quick start

```bash
cd assessment-agent-eval
python -m venv .venv && .venv\Scripts\activate     # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt

cp .env.example .env        # then paste your Gemini key (free: https://aistudio.google.com/app/apikey)

python run_eval.py --provider mock    # offline smoke test, no key needed
python run_eval.py                    # real run with Gemini (config.yaml default)
```

The report lands in `reports/<timestamp>_<promptversion>.html`. Open it in a browser.

## How it works

```
data/example_set_vN.csv ─┐
data/readings/*.txt      ─┤
rubric/rubric_vN.yaml    ─┼─► run_eval.py ─► AssessmentAgent ─► provider (LLM) ─► JSON
prompts/system_*.md      ─┘         │        (rubric rendered into the prompt's {{RUBRIC}} slot)
                                    ├─► compare vs expected labels
                                    ├─► runs/<ts>/results.json   (raw outputs, cached)
                                    ├─► reports/<ts>_<ver>.html  (the review artifact)
                                    └─► results_log.csv          (one row per run, for charting)
```

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

To add a brand-new backend: implement `complete()` in `src/providers/` and register
it in `src/providers/__init__.py`. For the real SENSEEI app, point `openai_compat`
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
(`src/agent.py`): it strips code fences, normalizes criterion names, and records
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
   - prompt wording → copy `prompts/system_prompt_vN.md` → next N
   - rubric → copy `rubric/rubric_vN.yaml` → next N
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
`rubric/rubric_v1.yaml`) so the 2026-06-19 baseline run stays reproducible.

## Layout

```
assessment-agent-eval/
├─ run_eval.py            entry point
├─ config.yaml            provider/model + pinned input versions
├─ .env.example           API keys (copy to .env)
├─ prompts/               versioned system prompts (system_prompt_vN.md; {{RUBRIC}} slot)
├─ rubric/                versioned rubric — single source of truth (rubric_vN.yaml)
├─ data/
│  ├─ example_set_vN.csv  labeled examples (matched to a rubric version)
│  └─ readings/sunk_cost.txt
├─ src/
│  ├─ rubric.py           loads the rubric YAML; criterion names + prompt rendering
│  ├─ agent.py            prompt assembly + JSON parse/validate + verdict derivation
│  ├─ compare.py          expected-vs-actual + stats
│  ├─ report.py           HTML rendering
│  └─ providers/          gemini / openai_compat / mock
├─ runs/                  raw JSON per run (reproducibility cache)
├─ reports/              timestamped HTML reports
├─ results_log.csv        per-run summary metrics
└─ CHANGELOG.md           per-iteration notes
```
