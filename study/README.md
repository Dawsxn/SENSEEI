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
demographics (5m) -> pre-test (5m) -> intervention (up to 40m)
    -> post-test A (10m) -> SBA (20m) -> [SUS (5m), SENSEE-I arm only]
```

Consent is not a phase. It is signed on paper before check-in — the participant
keeps one copy, the researchers retain the second (§4.6.4) — and the harness
records only that it was given, plus the form serial.

## The 40 minutes are a ceiling, not a floor

A participant who finishes the reading early continues straight to the post-test.
Nobody waits for the room. The period's only job is to end a session still
running when time is up.

> **This departs from the manuscript.** §4.6.4 as written says a participant who
> finishes early "remain[s] at their station until the period ends, so that
> exposure time is held constant across groups". That sentence needs revising to
> match, or the written method and the implementation disagree.
>
> The consequence: time-on-task now varies between participants and is no longer
> controlled by design, so the analysis has to account for it rather than the
> procedure having handled it. Recording per-phase durations is what makes that
> possible — see below.
>
> One thing it buys. §4.6.3's passive-arm criterion excludes someone who
> "advances to the post-test before a realistic minimum reading time has
> elapsed", which could never fire while everyone was held for the full period.
> It is live now.

**Group sizes must still come out 15/15/15.** Drawing each arm independently gets
there only 1.8% of the time. [`randomisation.py`](randomisation.py) generates a
permuted-block sequence once, from a recorded seed, and consumes it one slot per
check-in: exact totals, and near-balance at every prefix if the sitting ends
early.

## Exclusion measures (§4.6.3)

[`exclusion.py`](exclusion.py) gathers the quantities each arm's criterion is
judged on, and the console shows them live:

| Arm | Measured | From |
| --- | --- | --- |
| SENSEE-I | Session time, conversational turns | the app, via `senseei_link` |
| Unguided LLM | Session length, words typed | the chat transcript |
| Passive | Time before the post-test, time with the text open, scroll depth | the reader |
| All | Attention checks, per-phase durations, timed-out flag | the phase engine |

**No threshold is applied, and none is stored.** §4.6.3 derives the cutoffs
empirically from the pilot; one compiled into the tool could not be revised
without invalidating everything collected under it, and excluding a participant
would become a deployment artefact rather than an analytical decision. The module
reports numbers and computes running medians. Someone else decides what they
mean.

Three distinctions the console keeps apart, because collapsing any of them would
turn a technical failure into a finding about a participant:

- **Unknown is not zero.** A SENSEE-I participant who never opened the app has no
  telemetry; that reads as `—`, not as zero turns.
- **A failed tool is not disengagement.** If the arm's tool cannot start, the row
  says *tool failed* rather than showing zeros.
- **Running out of time is not low engagement.** It is flagged separately.

A row highlights when a measure sits at zero — almost always a broken tool rather
than an idle participant, and worth fixing while the session is still running.
It is explicitly *not* a cue to prompt someone to engage more: judging engagement
mid-run and nudging accordingly would be an unblinded intervention.

## Instruments

The five surveys live as YAML in [`instruments/content/`](instruments/content/)
and are served by one renderer. Two things follow from content being data:

**The faculty review reads what the tool serves.** §4.6.4 requires the pre-test,
post-test A, and the SBA case to pass content-validity review by two RVRCOB
faculty. The review document is *generated* from the same files the participant
is shown, so the two cannot drift and the review cannot end up certifying a
document nobody sat:

```bash
python -m study.instruments.review
```

It shows reviewers what participants never see — correct answers, attention
checks, and pre-test pairings — since those are exactly what a content review
judges. `status: reviewed` in the YAML records sign-off, and a live run is
refused while any instrument is still a draft.

**The pre-test / post-test pairing is declared.** §4.6.4 calls Part A "directly
related to the pre-test", and the retention comparison needs to know which item
answers which. `pairs_with` states it and the loader refuses a pointer that does
not resolve, so a renamed pre-test item cannot silently orphan its partner.

What ships now: **demographics** and the **SUS** are complete. The **pre-test**,
**post-test A**, and **SBA** are stubs — they cannot be written until the trial
reading is chosen, since every item is about the concept it covers. Each stub's
YAML carries the manuscript's requirements for what belongs in it.

The loader refuses content that would produce quietly meaningless data: an
attention check whose expected answer is not among its options (every
participant fails), a scored item whose answer is not among its options (every
participant is marked wrong), a SUS item with no polarity (the composite inverts
for half the scale).

The SUS is the one instrument not subject to §4.6.4 review — it is standardised,
not the researchers' to validate. Its alternating polarity is the instrument:
straight-lining lands at 50 whichever way you go, and there are tests for that.

## What is here

| Module | Holds |
| --- | --- |
| `arms.py` | The three arms |
| `randomisation.py` | Permuted-block allocation |
| `phases.py` | The session sequence and the 40-minute ceiling |
| `exclusion.py` | The §4.6.3 measures, gathered per arm |
| `senseei_link.py` | The only seam to the application |
| `trial_config.py` | Loads and validates `trial.yaml` |
| `trial.yaml` | **The one file to edit**: reading, model, timing, seed |
| `interventions/unguided.py` | The unguided-LLM arm |
| `interventions/passive.py` | The passive control arm |
| `interventions/conversation.py` | The chat transcript and what is measured from it |
| `instruments/` | The five surveys, as YAML plus a renderer and scorer |
| `instruments/review.py` | Generates the faculty content-validity document |

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

Still to come, in order: persistence, export and deletion, and the blind SBA
grading tool.

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
