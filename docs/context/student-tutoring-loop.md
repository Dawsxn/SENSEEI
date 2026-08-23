# Student tutoring loop

What a student does, and what the system does back, from opening the app to a
finished session.

## A session

One session is a single complete pass through all four SEE-I steps (State,
Elaborate, Exemplify, Illustrate) for one assigned reading. Steps are always
attempted in that order. A student who passes every step on the first try answers
exactly four questions.

A session ends in one of two ways:

| Ending | Cause |
| --- | --- |
| Complete | All four steps passed |
| Fallback | The student hit the maximum attempts on some step |

Both endings are terminal. A finished session of either kind is read-only, and
both give the student the option to start a new attempt at that reading.

A session cannot be paused. If a student tries to leave mid-session, the app asks
them to confirm, warning that the session will be discarded and cannot be
resumed. On confirmation the session is discarded.

There is no time limit on a session in the app.

## Entering a session

1. **Reading list.** The student opens the app to the readings assigned to the
   classes they are enrolled in. Enrolment determines visibility: a student sees
   a reading only if one of their classes has it assigned.
2. **Core components.** Each reading carries one or more core components, the
   essential defining parts of the concept, supplied by the instructor at upload.
3. **Already-attempted readings.** Selecting one shows a read-only view of the
   most recent session by default, with the option to start a new attempt
   (§4.3.1). Earlier sessions on that reading remain viewable. There is no cap on
   how many times a student may re-attempt a reading.
4. **Pre-reading screen.** Shows the text's metadata and the core component(s) to
   be studied.
5. **Reading.** The full text is shown. The student must explicitly tell the
   system they have finished. There is no automatic advance.
6. **Tutoring.** A split screen appears, reading on one half and chat on the
   other. The SEE-I process begins with State.

The reading stays visible for the whole session. Students are never asked to
recall the text from memory.

## The loop

Per step:

```
Tutor Agent asks
       │
       ▼
Student submits response
       │
       ▼
Assessment Agent grades against the rubric for this step
       │
       ├── PASS ──► more steps left? ── yes ──► advance, Tutor asks next step
       │                              └─ no ──► SESSION COMPLETE
       │
       └── FAIL ──► max attempts reached? ── no ──► Tutor explains what was
                                          │         missed, re-asks same step
                                          │
                                          └─ yes ─► FALLBACK, session ends
```

Pass/fail, retry, and step advancement are decided by the Orchestrator, which is
plain backend logic rather than an agent. It makes no LLM call.

The verdict it acts on is derived in code from the Assessment Agent's
per-criterion judgments: any failing criterion means FAIL. The agent's own stated
verdict is kept only as a self-consistency cross-check.

## Settled behaviour

These look like gaps but are decided. Do not change them without a reason.

1. **The attempt counter is per step, not per session.** The check is whether the
   student has reached the maximum attempts for that step (§4.4.2). Advancing to
   a new step starts its count fresh.
2. **On a retry the Tutor Agent receives the failed criteria and their reasons**
   from the Assessment Agent, and writes the feedback from them. It does not
   re-derive what went wrong. See [Feedback style](#feedback-style) for what that
   feedback contains.
3. **The Assessment Agent does not receive prior attempts.** Its inputs are the
   reading, the core components, the current step, and the response being graded
   (Table 4.7). Each attempt is judged on its own.
4. **The student can see how many attempts remain**, and the rubric itself is
   visible to the student in some form. The criterion vocabulary is not internal.

## Provisional values

Decided for now, not final. Keep each in a single place in code so changing it is
a one-line edit, not a search.

| Value | Setting |
| --- | --- |
| Maximum attempts per step | 3, uniform across all four steps |

## Dialogue moves

The Tutor Agent does not produce free-form conversation. It selects from a fixed
set of moves, chosen by the student's current step and the Assessment Agent's
verdict (Table 4.1).

| Move | Trigger | Purpose |
| --- | --- | --- |
| Prompt | Beginning of a step | Introduces the task and states what kind of response is required |
| Acknowledgement | Immediately after a response | Briefly acknowledges the attempt before the outcome |
| Criterion-Based Feedback | One or more criteria unmet | Says what was not satisfied, without supplying the correct response |
| Re-Prompt | After Criterion-Based Feedback | Invites a retry of the same step |
| Transition | All criteria satisfied | Confirms the step is complete |

Composition:

| Situation | Moves |
| --- | --- |
| First attempt at a step | Prompt |
| Failed, retries remain | Acknowledgement + Criterion-Based Feedback + Re-Prompt |
| Passed | Acknowledgement + Transition |

The Tutor Agent never supplies the answer. Feedback names what was missed and
redirects. The student revises their own response.

## Criteria by step

Feedback names the criteria that failed, so this vocabulary is user-facing.

| Step | Criteria |
| --- | --- |
| State | Brevity, Own Words, Clarity, Completeness, Accuracy |
| Elaborate | Completeness, Own Words, Coherence, Accuracy |
| Exemplify | Originality, Fit, Concreteness, Explicit Mapping, Contrast, Accuracy |
| Illustrate | Analogy, Match, Imagery, Accuracy |

Accuracy is the same criterion in all four steps: the response must be faithful
to the reading. Completeness in State and Elaborate is judged against the
reading's core components. State must name them, Elaborate must explain them.

The pass condition for every criterion lives in `agents/rubrics/rubric_vN.yaml`,
which is version-pinned and authoritative. The table above is orientation only.

## Feedback style

Feedback on a failed attempt has three parts, in this order:

1. **A plain-language account of what this response did wrong.** Specific to what
   the student actually wrote, not a restatement of the criterion.
2. **The names of the failed criteria.**
3. **A redirect**, restating the task with a corrective nudge that says what kind
   of change is needed, never the content of the answer.

Worked example, a State response that rambled (Table 4.2):

> You have the right idea, but your statement contains unnecessary tangents.
> Here's what you failed: Brevity, Clarity. Try stating what cognitive offloading
> is again, this time in a single focused sentence.

Part 1 is "your statement contains unnecessary tangents", part 2 is "Brevity,
Clarity", part 3 is "in a single focused sentence".

The same shape holds across the other steps. From Elaborate (Table 4.3): "your
response drifted into giving an example rather than extending the explanation of
the concept itself." From Exemplify (Table 4.4): "neither one explains how or why
it illustrates the concept."

Part 1 is what makes the Tutor Agent's job more than a lookup. Naming the
criterion alone would not require reading the response at all. Because part 1
describes the student's actual words, the Tutor Agent must receive the response
text, not only the failed criteria.

## Fallback

When a student exhausts their attempts on a step:

1. The session ends immediately. Remaining steps are not attempted.
2. A message advises the student to contact their instructor for further
   clarification.
3. A flag appears next to that student's name on the instructor's class roster.

The flag is half the purpose. The fallback prevents endless loops and student
frustration, and routes the student to a human who can review the reasoning chain
and intervene (§4.3.2). Ending the session without flagging does half the job.

## Related

- `docs/context/agent-contracts.md`, what each agent receives and returns
- `docs/context/data-model.md`, how sessions and judgments persist
- `agents/rubrics/`, the authoritative rubric
