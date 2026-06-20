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
data/example_set.csv ─┐
data/readings/*.txt  ─┼─► run_eval.py ─► AssessmentAgent ─► provider (LLM) ─► JSON verdict
prompts/system_*.md  ─┘         │
                                ├─► compare vs expected labels
                                ├─► runs/<ts>/results.json   (raw outputs, cached)
                                ├─► reports/<ts>_<ver>.html  (the review artifact)
                                └─► results_log.csv          (one row per run, for charting)
```

The agent checks **every** rubric row for the current step and collects **all**
failing criteria (it does not stop at the first failure), per the project spec.

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
rubric criterion — invaluable when tuning the prompt. Parsing is defensive
(`src/agent.py`): it strips code fences, normalizes criterion names, and records
warnings (hallucinated criteria, verdict/criteria mismatches) instead of crashing.

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
3. Change **one thing** — copy `prompts/system_prompt_v1.md` → `v2.md` and edit it
   (old versions are never overwritten). The run stamps the prompt version + hash
   into the report and `results_log.csv`.
4. Re-run, compare, and log the effect in `CHANGELOG.md`.
5. Repeat until the (TBD) per-step accuracy threshold is met.

`python run_eval.py --from-run runs/<dir>` rebuilds a report from saved raw outputs
without spending any API calls.

## Ground-truth fix (note for adviser review)

Two Exemplify examples originally labeled "reuses an example from the text" used
examples that were **not actually in `sunk_cost.txt`** (the reading contains only
the $5M airplane, $10k ERP training, and $200 snowboarding trip). They have been
**corrected** to reuse examples that genuinely appear in the reading:

- `F-EX-O-1` — was "Tom buys a movie ticket for $12.50"; now reuses the **snowboarding
  trip** (concrete + explicitly mapped, so it fails only Originality).
- `MC-EX-2` — was "Jennifer paid $100 to join a tutoring club"; now reuses the **ERP
  training** example, dropped without mapping (fails Originality + Explicit Mapping).

Like the rest of the set, these two should still be confirmed by Dr. Teehankee
before being treated as final ground truth.

## Layout

```
assessment-agent-eval/
├─ run_eval.py            entry point
├─ config.yaml            provider/model settings
├─ .env.example           API keys (copy to .env)
├─ prompts/               versioned system prompts (system_prompt_vN.md)
├─ data/
│  ├─ example_set.csv     labeled examples
│  └─ readings/sunk_cost.txt
├─ src/
│  ├─ rubric.py           canonical criterion names per step
│  ├─ agent.py            prompt assembly + JSON parse/validate
│  ├─ compare.py          expected-vs-actual + stats
│  ├─ report.py           HTML rendering
│  └─ providers/          gemini / openai_compat / mock
├─ runs/                  raw JSON per run (reproducibility cache)
├─ reports/              timestamped HTML reports
├─ results_log.csv        per-run summary metrics
└─ CHANGELOG.md           per-iteration notes
```
