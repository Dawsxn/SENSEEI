# SENSEEI — Assessment Agent Eval: Context Brief

## Thesis context
SENSEEI is an intelligent tutoring system that helps students build conceptual
understanding of academic readings using the **SEE-I framework**: State,
Elaborate, Exemplify, Illustrate. For each step, the student writes a response,
and a **Student Assessment Agent** (an LLM judge) decides PASS/FAIL against a
rubric of criteria specific to that step, listing every criterion it fails.

This eval harness (`assessment-agent-eval/`) develops and measures that one
agent in isolation, against a human-labeled set of example responses, before
it's wired into the full tutoring pipeline.

## The rubric
Each SEE-I step has several criteria. Each criterion has a single **PASS
condition** (pass-only schema — not meeting it means it fails; there's no
separate fail condition). The agent must judge **every** criterion for the
current step and collect **all** that fail — it never stops at the first
failure. The overall verdict is **derived in code**, not trusted from the
model: any failing criterion → FAIL, all passing → PASS.

Current rubric (v3), one universal grounding criterion (**Accuracy** — must be
faithful to the reading) added to all four steps:

- **State**: Brevity, Own Words, Clarity, Completeness, Accuracy
- **Elaborate**: Completeness, Own Words, Coherence, Accuracy
- **Exemplify**: Originality, Fit, Concreteness, Explicit Mapping, Contrast, Accuracy
- **Illustrate**: Analogy, Match, Imagery, Accuracy

Two new mechanics in v3:
- **Completeness** (State + Elaborate) is judged against a per-reading
  **core_components** reference — the professor-supplied essential parts of
  the concept (a CSV column). State must *name* them concisely; Elaborate
  must *explain* them in fullness.
- **Contrast** (Exemplify) is now a *required* criterion: every example must
  come with a genuine contrasting non-example that clarifies the concept's
  boundary (e.g., a near-miss that could be mistaken for the concept but isn't).

Rubric is versioned as YAML (`rubric/rubric_vN.yaml`) — the single source of
truth, rendered into the agent's system prompt and used by code for
validation/stats. A rubric change (rename/add/remove criteria) is always
paired with a matching relabeled example set of the same version.

## The evaluation process
1. **Versioned inputs, pinned per run** (`config.yaml`): a rubric version, a
   prompt version, and an example-set version. All three are stamped on every
   report/run/log row, so results are always traceable and reproducible.
2. **Labeled example set** (`data/example_set_vN.csv`): one row per test
   case — a reading, its core components, the SEE-I step, a student response,
   the expected verdict, which criteria it should fail (if any), and a
   `rationale` explaining why that's the ground truth. Examples are designed
   as **natural mistakes** (the errors real students are likely to make),
   mixing isolated single-criterion failures and realistic multi-criterion
   combinations, plus clean PASS controls (to catch over-flagging). Every
   criterion in the rubric must be exercised by at least one example.
3. **Run**: the harness sends each example through the agent (Gemini), which
   returns a JSON judgment (per-criterion pass/fail + reasons). The verdict is
   derived in code from those per-criterion results.
4. **Compare**: each result is scored against the label into one of four
   outcomes — *agree* (verdict + criteria both match), *criteria differ*
   (verdict right, flagged criteria differ), *verdict mismatch* (wrong
   PASS/FAIL), or *error* (no usable output, e.g. truncation).
5. **Report + log**: an HTML report (overall/per-step/per-criterion accuracy,
   token/cost, filterable per-example table) plus a row in
   `results_log.csv` (one row per run, for tracking trends across iterations)
   and a `CHANGELOG.md` entry (what changed, why, and the observed effect).

## Iteration discipline
Change **one thing at a time** (prompt wording, rubric criterion, or example
set) and bump only that input's version, so any accuracy shift is
attributable to a specific cause. Old versions are never edited in place —
always copy to a new `vN` file.

## Where things stand (latest run)
- v1 baseline (old rubric, 46 examples): 87.0% verdict accuracy.
- v2 (revised rubric, 18 examples): 94.4% verdict accuracy, 0 errors, ~$0.18.
- **v3 (current)** — new rubric with universal Accuracy, Completeness (core
  components), required Contrast; 3 new readings (strategy, business model,
  strategic vision), 70 examples: **78.6% verdict accuracy** (State 61.1% /
  Elaborate 80.0% / Exemplify 89.5% / Illustrate 83.3%), ~$0.95.
  State is the current weak point and the next thing to investigate/tune.
