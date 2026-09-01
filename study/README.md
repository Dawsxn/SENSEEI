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

Still to come, in order: the control-arm tools, the instruments, the proctor
console, export and deletion, and the blind grading tool. See the plan for
sequencing.

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
