# The trial

How the app supports the human evaluation: the three-group randomized controlled
trial in the manuscript (§4.6), run on its own instance with `TRIAL_MODE` on.

This records what was decided and why, so the trial work can be done as ordinary
pull requests against an agreed plan. The study design itself (sittings,
readings, the tests outside the app) is not final, so the app is built to fit
whatever it settles on rather than one arrangement.

**Built so far:** `TRIAL_MODE`, class modes, participant IDs in batches, sign-in
by ID, one session per participant, the session's 35 minutes, the two control
groups' screens, the event log, export, withdrawal by ID, the reliability fixes,
the instance's Blueprint (steps 3 to 9 of the order of work below), and the
pre-test and post-test taken in the app, with grading (below). What is left is
standing it up, the dry run, and the trial itself. Proposed changes to the study's procedure and
analysis, for the group to discuss, are in
`docs/thesis/human-evaluation-revisions.md`.

## The gate

The manuscript allows the trial only once the Assessment Agent reaches a
**criteria-exact rate of at least 80%** on the labelled dataset (§4.5.4): it must
name exactly the failing criteria, not only reach the right verdict. A trial run
with an agent that passes and fails the right answers for the wrong reasons would
not be testing SEE-I.

The latest run (`assessment-agent-eval/results_log.csv`, 2026-07-08, prompt v3,
70 examples) reached **43.48%**. That is the figure in the manuscript (§5.3), and
there has been no run since. Raising it is eval work, not app work, and it is the
longest item on the way to the trial.

## Three instances, one codebase

| | Development | Trial | Production |
| --- | --- | --- | --- |
| Purpose | QA | The study, and nothing else | Ordinary use, if the app gets any after the thesis |
| Deploys | Every merge to `develop` | On release to `main`; no releases during the trial | On release to `main` |
| `TRIAL_MODE` | Off | **On** | Off |
| Data | Fake seed | Study participants only | Real users |
| Lives | Indefinitely | The trial, then two years, then deleted | Indefinitely |

**Why a separate instance.** The trial has rules that ordinary use must not have:
one session per participant, a hard time limit, two control-group screens that
make no sense outside a study. And its data has rules ordinary data does not: keyed
to participant IDs, exported for analysis, deleted after two years. A database
holding only trial participants makes the export "everything in it" and the
deletion "this database". It deploys only releases to `main`, and nothing is
released from the first sitting until the last is done, so nothing merged
elsewhere can change the app between one sitting and the next.

**Why the same code.** The trial has to measure the SENSEE-I that ships, for the
same reason the eval must measure the agent the app uses: a copy kept for the
trial could drift, and then the results describe a system nobody runs.

**Production can wait.** The trial instance is the one that needs the paid server,
the paid database and the paid model key. Production is only needed if the app is
used for real beyond the thesis.

## `TRIAL_MODE`

One setting, `TRIAL_MODE=true`, read at startup, on for the trial instance and
off everywhere else. A participant's session time is 35 minutes, set in the code
(`trial_session_minutes`), and each test's time is in its test file, so none of
them can change between sittings without a release. The overrides exist only to
try the flow locally; the trial instance sets none of them.
One flag rather than several, because its rules come as a set: there is no useful
trial with one session per participant but no time limit, and every extra switch
is another combination that could be set wrong on the day.

Two rules for building it:

- **The server enforces it.** Hiding a button is not a rule. With trial mode on,
  the server refuses a second session, refuses sign-in outside an open batch, and
  ends sessions and tests at their time limits, whatever the browser sends.
- **The frontend asks the server.** `/auth/config` reports whether trial mode is
  on, as it already reports the dev bypass, so the screens and the rules cannot
  disagree.

What it changes:

| | Ordinary | Trial mode |
| --- | --- | --- |
| Who signs in | DLSU Google accounts | Participants by ID; the research team and the grader by Google, and no one else |
| Sessions per reading | Unlimited | One per participant |
| After a session ends | Start a new attempt | Nothing further |
| Time | No limit | 35 minutes, with time pop-ups but no visible countdown (plus each test's own) |
| A class | A SEE-I class | SEE-I, chatbot, or reading-only |
| Interaction events | Not recorded | Recorded (see below) |

## Groups, sittings and readings

A **sitting** is one block of participants in the lab at once. The manuscript fixes
45 participants, 15 per group, one on-campus lab, a timed intervention, and
the same reading for all three groups (§4.6.2–4.6.4). It does not fix how many
sittings there are, or whether every sitting uses the same reading.

So the app does not fix them either. **Each class has a mode and its own
readings**, and a participant's group is the class they belong to:

| Arrangement | Classes |
| --- | --- |
| One sitting, one reading | Three, one per group |
| Several sittings, same reading | The same three, used across days |
| A different reading per sitting | Three per sitting, each with that sitting's reading |

Changing the arrangement means creating different classes, not changing code.

## Participants: IDs and sign-in

The manuscript assigns each participant **a randomly generated identifier at the
point of consent**, and keys all performance records to it rather than to their
identity (§4.6.6). Identity is recorded on the consent and screening forms, for
attributing responses and verifying consent, and nothing identifying beyond that
is collected.

The trial instance honours this by **never holding identity at all**:

1. **The team makes a batch of IDs** on the Participants tab before a sitting,
   choosing how many each class gets: "5 for each of the three classes". Each ID
   looks like `P-7K3Q-9TXM`, in the same unambiguous alphabet as join codes, and
   nothing in it hints at the group. The batch page lists them by class, with a
   filter for one class and a copy button beside each ID.
2. **The slips are printed** grouped by class, or one class at a time with the
   filter. A line above each class's slips names it; it is cut off before the
   slips go into the bowl. A slip itself shows only the ID and where to enter it,
   never the class. **The fishbowl does the randomizing:** an equal number of
   slips per class goes in, so drawing assigns the groups at random, in equal
   numbers per sitting (block randomization).
3. **At consent**, the participant draws a slip and the researcher writes the ID
   on both consent copies. That form is the only place an ID meets a name, and
   the participant does not know their group until they sign in.
4. **At the computer**, the participant types their ID. It is their whole sign-in:
   no Google, no username, no password. It drops them into their class's mode.
5. **During the sitting**, a spoiled slip or someone who leaves is handled by
   voiding that one ID. It stops working at once.
6. **After the sitting**, the team closes the batch. Its IDs stop working, anyone
   still signed in with one is signed out, and any session still going ends as if
   time ran out, so nobody can return later and change their data.

A class's mode can be changed until its first participant signs in, then it is
fixed.

An ID works because it is random, only issued IDs exist, and a batch is open only
for its sitting. A password would add a second thing to get wrong in the lab and
protect nothing the ID does not.

The research team signs in with Google, as instructors (`INSTRUCTOR_EMAILS`). No
course faculty gets an instructor account on the trial instance, so no instructor
can learn who took part (§4.6.3). The grader (`GRADER_EMAILS`) signs in the same
way but sees only the grading page: participant IDs and their answers, never a
group or a class, so the grading stays blind.

**The team shares the trial.** Every instructor account sees and manages every
class, reading and batch on the trial instance, whoever made it, so anyone on the
team can void a slip or close a batch on the day. Outside trial mode each
instructor still sees only their own (`backend/services/ownership.py`).

**A trial class has one reading.** A participant is given their class's oldest
reading, so a second one would never be seen. The trial instance refuses to give
a class a second reading, at upload or when changing a reading's classes ("A class
you ticked already has a reading."). Replacing a reading means deleting the old
one first.

This also takes Google's sign-in settings out of the trial entirely: participants
never meet Google's consent screen, so its publishing status and test-user list
cannot block anyone on the day. In trial mode a Google account on neither
`INSTRUCTOR_EMAILS` nor `GRADER_EMAILS` is turned away, so the only way in for
anyone else is an ID.

## A participant's session time

- **The clock starts on Start in "Before you start"**, the one-line
  instructions every group sees over its reading, so nobody loses time before
  they are ready. The 35 minutes cover reading as well as the activity, as the manuscript's intervention phase does. The server
  holds the clock; the screen only follows it, so a reload does not restart it
  and nothing the browser sends buys more time.
- **No countdown is shown.** A running clock confused people in the user
  acceptance test. Instead a small card says "15 minutes left", then 5, then 1
  (`TimeNotices.tsx`); it stays until closed and never takes the cursor. The SEE-I
  group also gets one at 10 minutes into the reading, saying the session is
  waiting and the reading stays open beside it. The same in all three groups
  otherwise, so no group is treated differently. The pre-test's card comes at 1
  minute left, the post-test's at 10, 5 and 1.
- **At 0:00 everything stops.** The screen says time is up, and whatever was in
  progress is recorded as ended by time (`timed_out`, at the deadline itself).
  An answer sent after the deadline is not graded, with one exception: in the
  SEE-I group, an answer typed but not yet sent when time runs out is sent for
  them, graded and stored as their last attempt, and replied to (see below). That ending is kept and counted: the
  analysis is intention-to-treat (§4.6.2), so a session cut off at Exemplify
  counts exactly as one that reached Illustrate.
- **Finishing early ends the activity, not the sitting.** A SEE-I participant who
  completes all four steps sees that they are done and
  is given nothing further, and remains at their station until the period ends
  (§4.6.4).

### The SEE-I group

The ordinary tutoring loop, once. No "Start a new attempt" after it ends, no way
out of the session, and no class label on screen, since a class name could name
the group. A reload picks the session back up.

**No attempt limit.** On the trial instance a participant keeps trying a step
until they pass or their time runs out (`attempt_limit()` in
`backend/orchestrator.py`), so a trial session never ends in fallback and the
attempt dots are not shown. Elsewhere the limit is `MAX_ATTEMPTS`.

**An answer left in the box at time-up is sent for them.** The screen sends it
the moment it sees time is up, flagged `time_up`. The server takes it once and
only within `TIME_UP_GRACE` of the deadline, ends the session first, then grades
and stores it as an ordinary attempt. The reply says how it did without moving
on: a pass is acknowledged with no next question, a fail gets its feedback with
no request to try again. A pass on Illustrate marks the session complete. Grading
finishes even if they move on to the post-test meanwhile. It is logged as `time_up_submit`, with the
text itself if grading failed, since an attempt row is only written with its
judgment.

### The chatbot group (active control)

A general-purpose chat with **no pedagogical prompt**, on **the same model** and
settings as SENSEE-I's agents (§4.6.2), beside the same reading. Every message is
recorded with its time, as a SEE-I session is.

**The chatbot is given the reading**, and the participant is told so, both
in the "Before you start" popup and in a line above the chat. It is the reading
and nothing more: `SYSTEM_PROMPT` in `backend/services/chat_service.py` hands it
over and says only to use it as context, with no teaching instructions. So the
two AI groups now differ only in guidance, since both have the reading. (Until
the user acceptance test the chatbot was not given it; the adviser asked for it.)

**What it is, exactly:** the same provider, model, temperature and thinking level
as the agents, sent the whole conversation each turn with the reading as its
only system prompt. Its replies are shown the way a general-purpose chatbot shows them, with
lists and bold, and the participant's messages sit in grey rather than SEE-I's
green, so the screen does not read as SENSEE-I. A reload picks the conversation
back up. A reply that fails is not stored; the message that asked for it is, and
the failure is in the event log.

**Done** sits beside the countdown, green as it is on every screen. It asks first
("Finish now? You won't be able to send more messages.") and then ends the chat.

### The reading-only group (passive control)

The reading, the countdown, and a Done button. The time they press it is recorded,
because the exclusion rule for this group is finishing faster than the text can
realistically be read (§4.6.3). Done asks first ("Finish now? You can't undo
this."); the reading stays on screen afterwards.

### Before you start

Every group sees its instructions when its reading opens. Each names the goal,
understanding the reading's concept (its title, in a sentence), and says to press
Done only once they are confident they understand it:

| Group | Says |
| --- | --- |
| SEE-I | Their 35 minutes cover two parts: reading on this screen (about 10 minutes suggested), then the tutoring session, where the screen splits with the reading still beside the chat. Press Done only once confident |
| Chatbot | Read until they understand the concept; the chatbot beside it has the reading too, so they can ask it anything about it; press Done when confident |
| Reading only | Read until they understand the concept; press Done when confident |

It shows once. A participant who reloads partway does not see it again. Done asks
first: the SEE-I group's "Start the tutoring session?", and the control groups'
"Finish now?", which with tests says they go to the post-test and lose the reading
(and the chatbot).

### The briefing

Added after the user acceptance test, where people went in without knowing what
the study or SEE-I was (`frontend/src/features/trial/Briefing.tsx`). None of it is
timed: each stage's clock still starts on its own Start.

- **Welcome**, every group, before the pre-test's start screen: what the study is
  for, their group's steps as a flowchart with each step's minutes and the total,
  and that no timer is shown. The minutes come from `test_minutes` in `/trial/me`.
- **About SENSEE-I** and **How the session works**, the SEE-I group only, after
  the pre-test and before the reading, so the pre-test is answered without SEE-I
  in mind. The first defines the four steps as the rubric grades them (Illustrate
  is an analogy or metaphor, since the tool takes text only). The second is a
  labelled picture of the session screen: the reading, the steps, Components,
  Rubric (what an answer is graded on, changing with each step) and the chat box.

## What is recorded

Everything is keyed to the participant ID.

### Already recorded, for every SEE-I session

- Start and end time, and how it ended.
- Every attempt: the full text, its step, its number, and when it was submitted.
- The Assessment Agent's verdict on each attempt, and **each criterion's pass or
  fail with its reason**.
- Every tutor message, with its time and its dialogue moves.
- The model, prompt and rubric versions that graded it.

From these alone, without new code: time per step and per attempt, attempts per
step, where each participant stopped, which criteria failed on each attempt and
**which were fixed on the next** (direct evidence of whether the feedback worked),
answer length, and how much an answer changed between attempts. (The fallback
rate is always zero on the trial: there is no attempt limit there.)

### Added in trial mode: the event log

One row per interaction in `trial_event`, stamped with when it happened by the
participant's browser (and when the server received it). The browser sends what
only it can see in batches every few seconds, and once more as the page closes;
a batch that meets a lost connection or a server error is kept and sent again.
The server records what only it knows. Unknown kinds are refused, and a browser
clock more than an hour out is replaced by the server's.

Every event from a SEE-I participant's session also carries the `step` they were
on and the `attempt` they were about to make (`{"panel": "rubric", "step":
"Elaborate", "attempt": 2}`), and every event from the reading step carries
`"step": "Reading"`, so a row reads on its own without lining it up against the
transcript.

| Event | For |
| --- | --- |
| Event (`kind`) | For |
| --- | --- |
| Reading opened (`reading_opened`), Done pressed (`done`) | Reading time before starting; the reading-only exclusion rule |
| Rubric or core components panel opened and closed (`panel_opened`, `panel_closed`, with the panel) | How often, at which step, for how long, and whether opening it before a retry helps |
| PDF page changed (`page_changed`, with the page) | Whether participants returned to the text, and to which page |
| Tutor or chatbot reply finished streaming (`reply_shown`) | Time spent reading a reply before answering |
| First keystroke after each reply (`first_keystroke`) | Thinking time against typing time |
| Paste (`paste`, with its length only, never its content) | Relevant to the Own Words criterion, and to how the chatbot group used the reading |
| Left the tab and came back (`tab_left`, `tab_returned`) | Whether a participant left the app; a reload also counts as leaving |
| An AI turn failed (`turn_failed`, with where: assessment, tutor or chatbot) | Which participants had a rougher experience |

Two things the table used to list are recorded elsewhere, so they are not events:
**time running out** is the clock's start plus 35 minutes, and a SEE-I session
cut off by it ends `timed_out` on the step it was on; **chatbot messages** are
rows in `chat_message`, both sides of the conversation, with their times.

### Deliberately not recorded

Keystroke-by-keystroke typing, mouse movement, screen recording, the webcam. They
are far more invasive than any analysis here needs, and hard to square with
collecting nothing beyond what serves the study (§4.6.6).

## Exclusion rules

The manuscript excludes participants who did not genuinely engage (§4.6.3):

| Group | Excluded if below a threshold of |
| --- | --- |
| SEE-I | Total time, or number of turns |
| Chatbot | Session length, or words typed |
| Reading-only | Time before pressing Done |

The app excludes no one. It records these measures, and the team applies the
cut-offs during analysis. The cut-offs are set from the dry run's data before the
main trial, as the manuscript requires. Attention checks live in the surveys,
outside the app.

## Ethics, in the app's terms

These follow §4.6.3 and §4.6.6, except the fourth, which the manuscript does not
cover yet.

1. **No identity in the app.** Participants are their IDs; names exist only on
   consent forms.
2. **Only what serves the study.** Everything in the event log has a stated
   purpose above.
3. **The consent form says what is recorded.** The manuscript names session
   transcripts. The event log is behaviour, not answers, so the consent form and
   the ethics application must also say it is recorded. A plain version: *"The
   system records your answers, the time you spend, and how you use the on-screen
   panels and the reading."*
4. **Answers go to an outside AI service.** Every response is sent to Google's
   Gemini API to be graded. Use the paid tier for the trial, whose terms have not
   allowed Google to use submitted content to improve its products, as the free
   tier's have; check the current terms before the trial. Say in the consent form
   that responses are processed by an external AI service. The manuscript does not
   mention this yet.
5. **Only the research team has access**, to the instance and to the database.
6. **Two years after the defense, then deleted**, by deleting the trial instance
   and its database. A participant who withdraws earlier is deleted by ID, with
   everything under it.

## The pre-test and post-test

A class takes a test when its **Pre-test and post-test** setting names one. Tests
live in the code, one YAML file per reading in `backend/trial_tests`, with the
questions, the answer key, the rubrics and each test's time; the setting only
offers a test whose `reading_title` matches the class's reading exactly. Like the
mode, the setting is fixed once a participant signs in. A test changes only
through a release, so the same rule that freezes the app between sittings
freezes the test.

A participant in such a class goes through five stages, and the server decides
which one they are in (`test_stage` on `/trial/me`):

| Stage | What they see | Ends when |
| --- | --- | --- |
| `pretest` | The welcome, then "Pre-test", what it checks, "You have 5 minutes." and Start, then one written question. Its clock starts on Start. The reading is not shown | Submitted, or 5 minutes |
| `session` | The reading, chatbot or SEE-I session, as without tests. A SEE-I session's end replaces the answer box with a strip saying how it ended (complete, or time up) and Continue to post-test, so the last feedback stays readable. Time running out anywhere else (on the reading, or in a control group) shows a "Time's up" popup with the same button | Finished, Done, or 35 minutes |
| `posttest_ready` | "Post-test" and Start. Its clock starts on Start | Start pressed |
| `posttest` | 12 questions, with a question list and "I'm sure / I'm not sure" ticks. A tick is required on every answered question (Submit asks for any missing; a blank question needs none), but time running out submits everything as it is | Submitted, 30 minutes, or the batch closing |
| `done` | "You're done" | |

- **The reading and the session clock do not start before the pre-test ends**,
  and the post-test cannot start before the session ends. The server refuses
  both, whatever the browser sends.
- **Each test has its own clock**, kept out of sight like the session's. Finishing
  early moves straight on, so no one waits for a slower group.
- **Answers save as they are typed.** A test whose time runs out ends at its
  deadline with whatever was saved. Submitting asks first, since it cannot be
  undone.
- **Closed book.** The reading is never on screen during a test. Leaving the tab
  and pasting are logged as in the session, with `stage` set to `pretest` or
  `posttest`.
- **Each answer keeps its history:** when it was first answered, when last
  changed, and how many saves changed it.
- **Scoring.** Multiple choice is scored as it is saved. A written answer left
  blank scores 0 when its test ends. Every other written answer waits for the
  grader. The pre-test score, the post-test total (out of 20) and calibration
  appear once everything they depend on is scored. Calibration is the share of
  ticked answers whose tick matched the result: "sure" with full marks, or "not
  sure" without.
- **The batch page.** With tests, an ID shows Finished once its post-test has
  ended, not when its session does. Closing a batch ends any test still running
  as `closed`.

### Grading

The **Grading** tab lists every ID with test answers, by ID only, with how many
written answers are left. Opening one shows its pre-test and post-test totals,
calibration, the multiple choice with what was picked and whether it was right,
and each written answer with its tick, 0 to its points to click, and the rubric
(reference answer and criteria) beside it. A score saves when clicked and can be
changed at any time. The research team sees the same page, reached from the tab
or from an ID on a batch's page; the grader sees nothing else.

## Export

**Download data** on the Participants tab gives one zip, `senseei-trial-<date>.zip`,
of every batch. The download button on a batch's page gives the same zip for that
batch's IDs only, `senseei-trial-<batch name>-<date>.zip`, so a dry run can be
kept and then deleted without it ever mixing with a sitting. Both are
spreadsheet files, all keyed by participant ID, with a README saying what each
holds:

| File | One row per |
| --- | --- |
| `participants.csv` | ID: batch, class, group, signed in, reading opened, Done, time ran out, voided; with tests, each test's start and end, the scores and calibration |
| `tests.csv` | pre-test or post-test answer: the answer, the tick, the score, and its history |
| `sessions.csv` | SEE-I session: how it ended, the last step, and the versions that graded it |
| `attempts.csv` | SEE-I answer, with its verdict |
| `criteria.csv` | criterion judged on an answer, with the reason |
| `tutor_messages.csv` | thing the tutor said, with its dialogue moves |
| `chat_messages.csv` | chatbot message, either side |
| `events.csv` | event in the log |

They open directly in Excel, SPSS, R or Python; times are UTC. No file holds a
name or an email, since the instance never has any. Every column, and the
measures they give, are in `docs/context/trial-export.md`. Every participant from every
batch is included, whoever on the team made the batch.

## Withdrawal

A participant who withdraws gives the team their ID (or their name, which the
team looks up on the consent form). **Withdraw a participant** on the
Participants tab takes the ID and, after asking, deletes everything recorded for
it: the sessions and all they hold, the chat, the event log, the test answers,
and the ID itself. It cannot be undone. A withdrawal after an export means
deleting their rows from that export by hand too.

**Delete batch**, on a closed batch's page, does the same for every ID in it at
once. It is for clearing out the dry run (download its data first), and asks
first, since it cannot be undone.

## Reliability

Two things that could have cost a participant their one session:

- **A dropped connection.** A turn runs to the end and saves everything even if
  the browser stops listening partway (a closed lid, a reload mid-reply). The
  participant finds it all there when they come back.
- **A broken reply.** Where the session goes next (the next step, a retry, the
  end) is saved before the reply is written, so a reply that fails costs the
  message, not the participant's place. An opening question that never arrives
  leaves no session behind, so the participant can start again.

Nothing deletes an unfinished session. A participant cannot leave theirs, and one
cut off by time or by the batch closing ends `timed_out` and is kept.

## The order of work

1. **This document.**
2. **The agent gate**, in parallel: few-shot examples and a strict output format
   for the Assessment Agent, then re-run the eval until it reaches 80%.
3. **Trial mode basics:** the setting; class modes; participant IDs, batches and
   ID sign-in; one session per participant, enforced by the server.
4. **The session time:** the clock from the reading, the countdown, ending by time,
   and counting those sessions in the dashboard.
5. **The control groups:** the chatbot screen and the reading-only screen.
6. **The event log.**
7. **Export, and delete by ID.**
8. **Reliability:** the dropped-connection bug, and abandoned sessions handled the
   trial's way (kept, never deleted).
9. **The trial instance** in `render-trial.yaml`, a Blueprint of its own so it
   costs nothing until created: paid server and database, production rules,
   deploying each release to `main`.
10. **Stand it up:** release, the instance, a paid Gemini key, the classes and the
    reading.
11. **A dry run** through all three groups, to find what is broken and to set the
    exclusion cut-offs. Fix and release what it finds, then wipe the database.
12. **The trial.** No releases to `main` from the first sitting until the last.
13. **After:** export, analyse, keep two years, delete.

Each step with screens starts with mockups, as every screen in this app has.

## Open questions

- **The consent wording**, including the event log and the outside AI service,
  signed off by the adviser and the ethics application.
- **The sittings and readings.** The app does not need these settled; the classes
  do, before the dry run.

## Related

- `docs/context/student-tutoring-loop.md`, the session the SEE-I group runs
- `docs/context/data-model.md`, what is stored, and the retention rules
- `docs/context/tech-stack.md`, the instances and how they are deployed
