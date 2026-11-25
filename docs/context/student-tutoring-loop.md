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

Both endings are terminal. A finished session of either kind is read-only. In
place of the answer box, a strip says how it ended (Session complete, with "You
passed all four steps of SEE-I.", or Session ended, which adds nothing to the
fallback message already in the chat) and offers Back to reading, where the
student can start again, and Review session.

A session cannot be paused, and once left it cannot be resumed. If a student
tries to leave mid-session, by the exit or by the browser's back, the app asks
them to confirm, warning that the session will be discarded and cannot be
resumed. On confirmation the session ends as `left`: kept on the server, never
counted, and never offered back. A student who closes the tab instead leaves
their session `in_progress`, and it becomes `abandoned` when they next start the
same reading. Both are kept so that how often students quit partway, and on
which step, can be read back.

A reload is not leaving. The tab remembers the session it is in, so a reload
picks the same session back up from the server, with its conversation, its step
and the tries used. Closing the tab forgets it, and pressing Done on the reading
step starts a new one.

When something fails mid-session, a red strip says what, in the student's terms
(no connection, or something going wrong while starting or while sending an
answer), with Try again. Try again loads the session back as the server has it,
and sends the student's answer again only if the server never received it, so
nothing is typed twice and no try is counted twice. A reading that does not load
replaces the screen with "Couldn't load this reading." and Try again, or, when it
does not exist for the student, "This reading isn't available." and Back to
classes; no session starts behind it.

There is no time limit on a session in the app, except in trial mode.

**In trial mode** (`docs/context/trial.md`) a participant has no exit and their
session is picked back up after a reload from the server, as it always was; the
end strip and the error strip keep the trial's own wording. And three of these
rules change: a
participant gets exactly one session, with no new attempt after it ends; the 40
minutes from opening the reading are a hard limit, with a countdown; and a session
cut off by time is kept and counted, never discarded.

## Entering a session

1. **Classes, then readings.** The student opens the app to the classes they
   are enrolled in, each with how many readings it has, and opens a class to see
   its readings, with how many are still to do and how many are finished. Enrolment determines visibility: a student
   sees a reading only if one of their classes has it assigned.
2. **Core components.** Each reading carries one or more core components, the
   essential defining parts of the concept, supplied by the instructor at upload.
3. **Already-attempted readings.** The reading's page lists every past session
   on it, and each opens read-only under the reading (§4.3.1): a summary of the
   steps reached, then the conversation, with the criteria each answer missed
   shown as they were during the session, and the core components and rubric a
   tap away. The instructor sees the same page with the Assessment Agent's
   reason for each criterion. Starting again is from the reading's page. There
   is no cap on how many times a student may re-attempt a reading.
4. **Reading detail.** A page of its own under the class, showing the
   reading's core component(s), any past sessions on it, and Start.
5. **Walkthrough, the first time only.** Before a student's first session on
   any reading, Start goes through three screens: the four SEE-I steps, how a
   session runs (the reading alone, then the tutoring screen with the reading
   still available, then the end), and what the core components and the rubric
   are. Seeing it is recorded on the account, so it does not show again on
   another device; the help icon in the top bar opens it any time. The trial
   keeps its own briefing and never shows this.
6. **Reading step.** The reading is shown on its own, as the instructor's
   original PDF where one is stored and as the extracted text otherwise. An
   opening dialog names the concept the session is about. The student must
   explicitly tell the system they have finished; there is no automatic advance,
   and the button is never gated on scroll position, because scrolling is not
   reading. Back returns to the reading's page, after asking, since the student
   would lose their place.
7. **Tutoring.** A split screen appears, reading on one half and chat on the
   other. The SEE-I process begins with State.

**The session is created at the end of step 6, not the start of step 7.** Opening
a reading and leaving therefore records nothing. A student who reaches step 7
and leaves still leaves a row behind, as `left` or, if they closed the tab,
`abandoned` once they start the reading again.

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
| Maximum attempts per step | 5, uniform across all four steps (`MAX_ATTEMPTS` in `backend/orchestrator.py`). None on the trial instance, where a step runs until it passes or time runs out (see `trial.md`) |

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
| Failed, no retries remain | Acknowledgement + Criterion-Based Feedback |
| Passed | Acknowledgement + Transition |

The third row is not a fifth dialogue move. It is the second with `Re-Prompt`
dropped, since there is no attempt left to invite. The student still gets the
feedback, because they and their instructor both need to know what went wrong on
the last try.

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

Feedback on a failed attempt has three parts. Two the Tutor Agent writes, one
the interface shows:

1. **A plain-language account of what this response did wrong.** Specific to what
   the student actually wrote, not a restatement of the criterion.
2. **The names of the failed criteria**, displayed beside the message rather
   than spoken inside it.
3. **A redirect**, restating the task with a corrective nudge that says what kind
   of change is needed, never the content of the answer.

Worked example, a State response that rambled (Table 4.2):

> You have the right idea, but your statement contains unnecessary tangents. Try
> stating what cognitive offloading is again, this time in a single focused
> sentence.
>
> `Brevity` `Clarity`

Part 1 is "your statement contains unnecessary tangents", part 3 is "in a single
focused sentence", and part 2 is the two tags.

**The names are a UI element, not prose, as of tutor prompt v2.** They travel
with the message as data, which is what lets them be shown as labels the student
can scan rather than words to find inside a paragraph. v1 recited them in the
sentence; sessions pinned to it still replay that way.

What each criterion asks for is not in the message at all. The student opens the
Rubric panel from the session's top bar, which shows the rubric's own wording for
the step they are on. The per-criterion *reason* the Assessment Agent gave is
never shown: it says where the response went wrong, and the Tutor is forbidden
from pointing at that.

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
   clarification. **This message is static, not written by the Tutor Agent.** It
   is identical every time, and generating it would invite the model to soften
   it or add a hint that cannot be acted on.
3. A flag appears next to that student's name on the instructor's class roster.

The flag is half the purpose. The fallback prevents endless loops and student
frustration, and routes the student to a human who can review the reasoning chain
and intervene (§4.3.2). Ending the session without flagging does half the job.

## Related

- `docs/context/agent-contracts.md`, what each agent receives and returns
- `docs/context/data-model.md`, how sessions and judgments persist
- `agents/rubrics/`, the authoritative rubric
