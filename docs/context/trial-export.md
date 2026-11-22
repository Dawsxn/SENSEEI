# The trial export

What **Download data** on the Participants tab gives you: one zip,
`senseei-trial-<date>.zip`, of spreadsheet files. This lists every file and every
column. How the data is collected is in `docs/context/trial.md`.

**Read this first**

- Every file is keyed by `participant_id`, the ID on the participant's slip
  (`P-7K3Q-9TXM`). Join files on it, and join the Google Forms responses (tests,
  surveys) on it too.
- No file holds a name or an email. The app never has any.
- Times are UTC, in ISO 8601 (`2026-10-28T01:04:12+00:00`). Manila is UTC+8.
- Every participant from every batch is included. A withdrawn participant is
  gone from every file.
- The files open in Excel, SPSS, R or Python as they are.

## participants.csv

One row per participant ID. Every group.

| Column | Meaning |
| --- | --- |
| participant_id | The ID |
| batch | The batch it came from, e.g. `Sitting 1` |
| class | The class it was in, e.g. `TRIAL S1-A` |
| group | `seei`, `chatbot` or `reading_only` |
| signed_in_at | First sign-in. Empty if never used |
| reading_opened_at | When the reading opened. Their session time starts here |
| done_at | When they pressed Done. Chatbot and reading-only groups only |
| time_ran_out_at | When their session time ended. Empty if the reading never opened |
| voided_at | When the ID was voided. Empty if it was not |
| test | The test their class took, e.g. `strategic_offensives`. Empty without tests |
| pretest_started_at, pretest_ended_at | When the pre-test started and ended |
| pretest_ended_by | `submitted`, `time_up`, or `closed` (the batch closed while it ran) |
| posttest_started_at, posttest_ended_at, posttest_ended_by | The same for the post-test |
| pretest_score | 0 to 3. Empty until it is graded |
| posttest_total | 0 to 20. Empty until every answer is scored |
| calibration | The share of "sure / not sure" ticks that matched the result, 0 to 1. Empty until every ticked answer is scored |
| sure_but_wrong | Answers ticked "sure" that did not get full marks |

## sessions.csv

One row per SEE-I session. The SEE-I group only; one session per participant.

| Column | Meaning |
| --- | --- |
| participant_id | |
| session_id | Links to `attempts.csv`, `criteria.csv` and `tutor_messages.csv` |
| reading | The reading's title |
| status | `complete` (passed all four steps), `fallback` (ran out of attempts), `timed_out` (ran out of time), or `in_progress` |
| last_step | The step they ended on: where they stopped, or `Illustrate` if complete |
| started_at | When they pressed Done on the reading and the session began |
| ended_at | When it ended. For `timed_out`, exactly when the session time ran out |
| rubric_version, tutor_prompt_version, assessment_prompt_version, model | What graded and tutored this session |

## attempts.csv

One row per SEE-I answer.

| Column | Meaning |
| --- | --- |
| participant_id, session_id | |
| step | `State`, `Elaborate`, `Exemplify` or `Illustrate` |
| attempt_number | 1, 2 or 3 on that step |
| submitted_at | When they sent it |
| verdict | `PASS` or `FAIL`. Fails if any criterion failed |
| model_verdict | What the model itself said. Usually the same as `verdict`; a difference is worth a look |
| response_text | Their answer, word for word |

## criteria.csv

One row per criterion judged on each answer. The most-failed criteria come from
here.

| Column | Meaning |
| --- | --- |
| participant_id, session_id, step, attempt_number | Which answer |
| criterion | e.g. `Own Words`, `Brevity` |
| passed | `True` or `False` |
| reason | The Assessment Agent's reason. Never shown to the participant |

## tutor_messages.csv

One row per message the tutor showed. SEE-I group only.

| Column | Meaning |
| --- | --- |
| participant_id, session_id, step | |
| moves | The dialogue moves it was made of, e.g. `Acknowledgement + Criterion-Based Feedback + Re-Prompt`. `Fallback` is the fixed message after the last failed attempt |
| created_at | When it finished |
| content | The message, word for word |

## chat_messages.csv

One row per chatbot message, both sides. Chatbot group only.

| Column | Meaning |
| --- | --- |
| participant_id | |
| role | `user` (the participant) or `assistant` (the chatbot) |
| created_at | When it was sent or finished |
| content | The message, word for word |

A question with no `assistant` row after it is one whose reply failed (see
`turn_failed` below).

## events.csv

One row per thing a participant did. Every group.

| Column | Meaning |
| --- | --- |
| participant_id | |
| kind | What happened. Listed below |
| data | Details, as JSON. Which ones depends on the kind |
| at | When it happened, by the participant's computer |
| received_at | When the server got it. Normally a few seconds after `at` |

In the SEE-I group, `data` also has `step` and `attempt`: the step they were on
and the attempt they were about to make (`{"panel": "rubric", "step":
"Elaborate", "attempt": 2}`). On the reading screen before the session, `step` is
`Reading`.

| kind | Means | data |
| --- | --- | --- |
| reading_opened | The reading opened; their time started | |
| done | Pressed Done (chatbot, reading only) | |
| panel_opened | Opened the Rubric or Components panel (SEE-I) | `panel`: `rubric` or `components` |
| panel_closed | Closed it | `panel` |
| page_changed | Moved to another page of the PDF | `page` |
| reply_shown | A tutor or chatbot reply finished arriving | |
| first_keystroke | First key typed after a reply | |
| paste | Pasted text into the answer or message box | `length`: characters pasted. Never the text |
| tab_left | Left the page: another tab or window, or a reload | |
| tab_returned | Came back | |
| turn_failed | An AI reply failed. Nothing was graded or lost; they sent it again | `where`: `assessment`, `tutor` or `chatbot` |

## tests.csv

One row per pre-test or post-test answer. Only for classes with tests.

| Column | Meaning |
| --- | --- |
| participant_id | |
| test | `pre` or `post` |
| question | The question's id in the test file: `pre`, `q1` to `q11`, `q12a`, `q12b` |
| part, dimension | The post-test part (A to D) and what it measures: `facts`, `connections`, `transfer`, `metacognition` |
| kind | `choice`, `text`, or `groups` (the 12a table) |
| answer | The letter picked, the text written, or the 12a table as JSON |
| sure | `True` for "I'm sure", `False` for "I'm not sure". Empty if not ticked |
| score | The points it got. Empty until graded |
| max_score | What full marks are worth. Empty for 12a, which is not scored |
| first_answered_at, last_changed_at | When it was first answered and last changed |
| edits | How many saves changed it |
| scored_at | When it was scored |

## What you can work out from these

| Measure | From |
| --- | --- |
| Time on the reading before starting (SEE-I) | `sessions.started_at` minus `participants.reading_opened_at` |
| Total time (SEE-I) | `sessions.ended_at` minus `participants.reading_opened_at` |
| Turns (SEE-I) | Rows in `attempts.csv` |
| Attempts to pass each step | `attempts.csv`: the `attempt_number` of the `PASS` row |
| Criteria fixed after feedback | `criteria.csv`: failed on attempt n, passed on attempt n+1 |
| Thinking time | `first_keystroke` minus the `reply_shown` before it |
| Session length (chatbot) | Last `chat_messages.created_at`, or `done_at`, minus `reading_opened_at` |
| Words typed (chatbot) | Words in the `user` rows of `chat_messages.csv` |
| Pasted from the reading (chatbot) | `paste` events, and their lengths |
| Time before Done (reading only) | `participants.done_at` minus `reading_opened_at` |
| Rough experience | Count of `turn_failed` per participant |
| Score per dimension | `tests.csv`: `score` summed by `dimension` |
| Time on each test | `*_ended_at` minus `*_started_at` in `participants.csv` |
| Looking things up during a test | `tab_left` and `paste` events whose `data` has `stage` `pretest` or `posttest` |
