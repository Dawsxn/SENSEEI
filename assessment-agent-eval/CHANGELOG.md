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

---

## v2 — 2026-06-23  (rubric overhaul + versioned inputs — new baseline)
- **Changed (multiple, coordinated — this is a fresh baseline, not an attributable delta from v1):**
  - **New rubric, re-derived from the source book** (`rubric/rubric_v2.yaml`). Criteria are now: State = Brevity / Clarity / Accuracy; Elaborate = Expansion / Own Words / Coherence; Exemplify = Originality / Fit / Concreteness / Explicit Mapping; Illustrate = Comparison / Match / Imagery. Dropped v1 criteria that weren't grounded in the text (Length, State-Originality, Scope, Jargon Translation, Relationship Accuracy).
  - **Pass-only single-gate schema.** Each criterion has one PASS condition; it fails if that condition isn't met (no separate fail column). The prompt's "how to apply" was rewritten to match.
  - **Versioned, independently-pinned inputs.** Rubric is now the single source of truth (YAML), rendered into the prompt's `{{RUBRIC}}` placeholder; `prompt_version` / `rubric_version` / `example_set_version` are pinned in `config.yaml` and stamped on the report, `results.json`, and `results_log.csv`. `prompt_hash` now hashes the *composed* prompt (prompt + rubric). Baseline retroactively frozen as `rubric_v1.yaml` + `example_set_v1.csv`.
  - **Verdict is now derived in code** from the per-criterion judgments (any fail → FAIL). The model's stated verdict is kept only as a self-consistency cross-check (warns on mismatch).
- **Why:** several v1 criteria contradicted or weren't in the reading; the two-column pass/fail created ambiguity; and the rubric/example set needed to be reproducible and independently versionable for iteration.
- **Data note:** `example_set_v2.csv` is a fresh, human-verified set — 18 rows (8 PASS controls + 10 natural-mistake FAILs), drastically reduced from v1's 46. Focus on the most likely natural mistakes; every one of the 13 criteria has at least one failing example (Concreteness and Imagery added as isolated coverage probes).
- **Run:** `gemini-3.1-pro-preview`, thinking level **low**, `max_output_tokens` 4096, 18 examples. Report: `reports/20260623_030537_v2.html`.
- **Result:** overall verdict accuracy **94.4% (17/18)**. Per-step: State **100%** (4/4) / Elaborate **100%** (4/4) / Exemplify **100%** (5/5) / Illustrate **80%** (4/5). Criteria exact-match (FAILs): **80%** (8/10). Status: 16 agree / 1 criteria-differ / 1 verdict-mismatch / **0 errors**. Tokens: 33,886 in / 5,744 thinking / 3,749 out. Cost: **~$0.18**.
- **Observed effect:**
  - **0 errors** — the 4096 ceiling + `thinking_level: low` eliminated v1's 4 JSON truncations (thinking dropped to ~319 tokens/example).
  - The only two deviations are precisely the two cases flagged as borderline when the set was designed:
    - **I-M-1 (the lone verdict miss):** the "spilled milk" Match probe — the agent judged the analogy adequately captures the concept and **passed** it, where the label expects a Match failure (surface-only similarity).
    - **S-BC-1 (the lone criteria-differ):** verdict correct (FAIL), but the agent **also flagged Accuracy** on top of Brevity + Clarity — the deliberate "should Accuracy stay unflagged on a vague-but-not-false statement?" edge case.
  - Every other probe was exact, including the isolated/coverage ones: Concreteness (EX-C-1), Imagery (I-IM-1), Comparison-only (I-C-1), Fit (EX-F-1), and both multi-criteria FAILs (E-EO-1, EX-OE-1).
- **Next:** Illustrate's **Match** is the only soft spot. Decide with Dr. Teehankee whether I-M-1 and S-BC-1 are agent errors or labels worth revisiting, then make **one** targeted change (Match wording in the prompt, or the label) and re-run to attribute the effect.
