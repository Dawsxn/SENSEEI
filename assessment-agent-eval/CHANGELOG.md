# Iteration Changelog — Student Assessment Agent

One entry per iteration. Change **one thing at a time** (prompt *or* rubric) so
each accuracy shift can be attributed. Pull the numbers from the run's HTML
report (or `results_log.csv`). Newest entries go at the **bottom** so the file
reads top-to-bottom as the agent's evolution.

Template to copy for each new entry:

```
## <prompt version> — YYYY-MM-DD
- **Changed:** what you edited (prompt section / rubric criterion).
- **Why:** the failure pattern in the previous run that motivated it.
- **Run:** provider/model, thinking level, report file.
- **Result:** overall verdict accuracy __% (prev __%). Per-step: State __ / Elaborate __ / Exemplify __ / Illustrate __. Criteria exact-match __%.
- **Observed effect:** what improved / regressed; which criteria the agent still mis-catches.
- **Next:** hypothesis for the next change.
```

---

## v1 — 2026-06-19  (baseline)
- **Changed:** Initial draft of the system prompt from the SEE-I rubric. First run, nothing to compare against.
- **Data note:** Labeled set includes a correction to two Exemplify "Originality" examples (`F-EX-O-1`, `MC-EX-2`) that originally referenced examples not present in the reading (see README).
- **Run:** `gemini-3.1-pro-preview`, thinking level **high** (model default — this run predated thinking-level control), `max_output_tokens` 2048. Report: `reports/20260619_170457_v1.html`.
- **Result:** overall verdict accuracy **87.0% (40/46)**. Per-step: State **100%** (14/14) / Elaborate **83.3%** (10/12) / Exemplify **70%** (7/10) / Illustrate **90%** (9/10). Criteria exact-match (FAILs): **55.3%** (21/38). Status: 27 agree / 13 criteria-differ / 2 verdict-mismatch / **4 errors**.
- **Observed effect:**
  - The 4 "errors" were **JSON truncations**, not agent mistakes: `max_output_tokens` (2048) was too small once Pro's thinking tokens counted against it, cutting the JSON off mid-response. Excluding them, the agent got **40/42 valid verdicts right (~95%)**.
  - Only **2 genuine verdict disagreements**: `P-EX-2` (a valid Exemplify answer wrongly marked FAIL) and `F-I-SM-2` (a superficial analogy wrongly marked PASS on Structural Match).
  - Criteria identification is the main soft spot (13 "criteria differ"), concentrated in Exemplify/Illustrate.
- **Cost:** ~$0.76 USD (from the billing console; this run predated token/cost logging).

### Setup changes applied after the v1 run (affect the next run, not v1's numbers)
- `max_output_tokens` 2048 → 4096 (fixes the truncations).
- `thinking_level: low` set for production consistency (v1 ran at high).
- Migrated to the official `google-genai` SDK; added per-run token + cost logging and `finish_reason` capture.
- **Next:** Re-run the labeled set at `thinking_level: low` for the production-consistent baseline (real token/cost numbers, no truncations), then begin prompt tuning on the weakest criteria (Exemplify/Illustrate identification).
