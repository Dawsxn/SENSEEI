# Human-evaluation harness

Everything that surrounds the SENSEE-I application during the three-arm
randomised controlled trial of §4.6. Participant lifecycle, randomisation, the
phase engine, the two control-arm tools, the instruments, the exclusion
telemetry, the blind SBA grading tool, and the export.

## The boundary

**This package does not contain any part of the SENSEE-I application, and never
edits it.** The app is built separately. The two meet at exactly one file,
[`senseei_link.py`](senseei_link.py), and nothing else in here may import from or
reach into the app.

That boundary is not tidiness. It is what lets the app change on its own schedule
without breaking the trial tooling, and it is what lets the harness be built,
tested, and dry-run end to end *today*, against `FakeSenseeiLink`, before the
application exists.

Three things are asked of the app, and everything else is the harness's own job:

| Need | Why |
| --- | --- |
| Where to send a participant | So they can do their tutoring session |
| What that session did | Exclusion criteria (§4.6.3) and the export |
| How to delete it | The right to withdraw (§4.7.1) |

Notably absent: the app is never asked to enforce the 40-minute clock, and no
phase ever advances because the app said so.

## The trial

45 RVRCOB undergraduates, 15 per arm (§4.6.3).

| Arm | Intervention |
| --- | --- |
| SENSEE-I | The real tutoring system, run in the app |
| Unguided LLM | General-purpose chat, no pedagogical system prompt, **same model** as SENSEE-I's agents (§4.6.2) |
| Passive control | The same expository text, read without any tool |

Every participant runs the same sequence (Table 4.11):

```
demographics (5m) -> pre-test (5m) -> intervention (40m)
    -> post-test A (10m) -> SBA (20m) -> [SUS (5m), SENSEE-I arm only]
```

Consent is not a phase. It is signed on paper before check-in — the participant
keeps one copy, the researchers retain the second (§4.6.4) — and the harness
records only that it was given, plus the form serial.

## Two things that would silently ruin the study

Both are covered by tests, because both fail quietly.

**Exposure time must be equal across arms.** §4.6.4 gives everyone the same 40
minutes and holds early finishers at their station. If a fast SENSEE-I
participant could start the post-test at minute 25 while a passive-arm
participant read for the full 40, the arms would differ in time-on-task as well
as in instructional mode, and the independent variable would no longer be the one
the study claims. [`phases.py`](phases.py) gates on time, not completion.

**Group sizes must come out 15/15/15.** Drawing each arm independently gets there
only 1.8% of the time. [`randomisation.py`](randomisation.py) generates a
permuted-block sequence once, from a recorded seed, and consumes it one slot per
check-in: exact totals, and near-balance at every prefix if a batch ends early.

## What is here

| Module | Holds |
| --- | --- |
| `arms.py` | The three arms |
| `randomisation.py` | Permuted-block allocation |
| `phases.py` | The session sequence and the 40-minute gate |
| `senseei_link.py` | The only seam to the application |
| `trial_config.py` | Loads and validates `trial.yaml` |
| `trial.yaml` | **The one file to edit**: reading, model, timing, seed |
| `interventions/unguided.py` | The unguided-LLM arm |
| `interventions/passive.py` | The passive control arm |
| `interventions/conversation.py` | The chat transcript and what is measured from it |

Changing the trial reading is one line in `trial.yaml`; the text itself goes in
`content/`. The model is pinned there too, and `assert_model_parity` checks the
pin against what SENSEE-I actually runs rather than trusting two files to agree.

## No model is baked in

The unguided arm reaches the model through `agents/providers/`, so switching
model or provider is a line in `trial.yaml` and never a code change. The seam is
`ChatBackend` rather than the provider itself, because the shared provider
interface is single-turn and a chat is not: `ProviderChatBackend` bridges the two
by rendering the transcript into the prompt, which needed no change to the agent
code the eval measures.

That bridge is an approximation — a provider given structured messages applies
its own chat template, which flattening does not reproduce exactly. It is the
same model either way, so §4.6.2's parity requirement holds. If native multi-turn
fidelity later matters, a second `ChatBackend` slots in behind the same protocol
without touching a caller.

Still to come, in order: the instruments, the proctor console, export and
deletion, and the blind grading tool.

## Seeing it

```bash
pip install -e ".[study]" && python -m uvicorn study.api.app:app --reload
```

Open <http://127.0.0.1:8000>. That is the **proctor console**: check someone in
and it assigns their arm from the pre-generated allocation and hands you their
participant link. Open the link to see what that participant sees — which of the
three intervention screens they get depends on the arm they drew.

The console shows a pre-flight banner listing whatever would stop this being real
collection: records held in memory, no trial id, the sample reading still in
place, no model reachable. A proctor should never have to guess whether they are
looking at a rehearsal or the real thing.

Two things are deliberately not real yet. Participants live in memory, so a
restart loses them — the persistence layer is a later step, and building it
before the flow settled would mean migrating a moving schema. And the instrument
phases render a placeholder, pending their content and its faculty review.

**Server-rendered HTML, not a SPA.** The application is React because it is a
long-lived product. This is a lab instrument used by 45 people on one afternoon,
and a build toolchain would be machinery to maintain for nothing a participant
would ever notice.

## Running the tests

```bash
python -m pytest study/tests -q
```

## Thresholds are not in the code

§4.6.3 derives the exclusion cutoffs empirically from a pilot, so the harness
records the raw quantities — session time, turn count, word input, time on the
reading, per-phase durations, attention-check results — and the analysis applies
cutoffs afterwards. A threshold compiled into the tool could not be revised
without invalidating the data collected under the old one.
