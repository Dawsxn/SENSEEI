# The trial

How the app supports the human evaluation: the three-group randomized controlled
trial in the manuscript (§4.6), run on its own instance with `TRIAL_MODE` on.

This records what was decided and why, so the trial work can be done as ordinary
pull requests against an agreed plan. The study design itself (sittings,
readings, the tests outside the app) is not final, so the app is built to fit
whatever it settles on rather than one arrangement.

**Built so far:** `TRIAL_MODE`, class modes, participant IDs in batches, sign-in
by ID, one session per participant, the 40 minutes, the two control groups'
screens and the event log (steps 3 to 6 of the order of work below). Export and
the instance itself are still to come. Proposed changes to the study's procedure and
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
| Deploys | Every merge to `develop` | Once, from a fixed release, then frozen | On release to `main` |
| `TRIAL_MODE` | Off | **On** | Off |
| Data | Fake seed | Study participants only | Real users |
| Lives | Indefinitely | The trial, then two years, then deleted | Indefinitely |

**Why a separate instance.** The trial has rules that ordinary use must not have:
one session per participant, a hard 40 minutes, two control-group screens that
make no sense outside a study. And its data has rules ordinary data does not: keyed
to participant IDs, exported for analysis, deleted after two years. A database
holding only trial participants makes the export "everything in it" and the
deletion "this database". Frozen at one release, nothing merged elsewhere can
change the app between one sitting and the next.

**Why the same code.** The trial has to measure the SENSEE-I that ships, for the
same reason the eval must measure the agent the app uses: a copy kept for the
trial could drift, and then the results describe a system nobody runs.

**Production can wait.** The trial instance is the one that needs the paid server,
the paid database and the paid model key. Production is only needed if the app is
used for real beyond the thesis.

## `TRIAL_MODE`

One setting, `TRIAL_MODE=true`, read at startup, on for the trial instance and
off everywhere else. `TRIAL_MINUTES` (default 40) sets a participant's time.
One flag rather than several, because its rules come as a set: there is no useful
trial with one session per participant but no time limit, and every extra switch
is another combination that could be set wrong on the day.

Two rules for building it:

- **The server enforces it.** Hiding a button is not a rule. With trial mode on,
  the server refuses a second session, refuses sign-in outside an open batch, and
  ends sessions at 40 minutes, whatever the browser sends.
- **The frontend asks the server.** `/auth/config` reports whether trial mode is
  on, as it already reports the dev bypass, so the screens and the rules cannot
  disagree.

What it changes:

| | Ordinary | Trial mode |
| --- | --- | --- |
| Who signs in | DLSU Google accounts | Participants by ID; the research team by Google, and no one else |
| Sessions per reading | Unlimited | One per participant |
| After a session ends | Start a new attempt | Nothing further |
| Time | No limit | 40 minutes, with a countdown |
| A class | A SEE-I class | SEE-I, chatbot, or reading-only |
| Interaction events | Not recorded | Recorded (see below) |

## Groups, sittings and readings

A **sitting** is one block of participants in the lab at once. The manuscript fixes
45 participants, 15 per group, one on-campus lab, a 40-minute intervention, and
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
   nothing in it hints at the group. The IDs are drawn in a shuffled order.
2. **The slips are printed** in that order: the ID and where to enter it, never
   the class. Handing them out from the top of the stack assigns the groups at
   random, in equal numbers per sitting (block randomization).
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
can learn who took part (§4.6.3).

This also takes Google's sign-in settings out of the trial entirely: participants
never meet Google's consent screen, so its publishing status and test-user list
cannot block anyone on the day. In trial mode a Google account that is not on
`INSTRUCTOR_EMAILS` is turned away, so the only way in for anyone else is an ID.

## A participant's 40 minutes

- **The clock starts when the reading opens.** The 40 minutes cover reading as
  well as the activity, as the manuscript's intervention phase does. The server
  holds the clock; the countdown only draws it, so a reload does not restart it
  and nothing the browser sends buys more time.
- **A countdown is visible**, the same in all three groups, so no group is
  treated differently. It turns amber in the last five minutes.
- **At 40:00 everything stops.** The screen says time is up, and whatever was in
  progress is recorded as ended by time (`timed_out`, at the deadline itself).
  An answer sent after the deadline is not graded. That ending is kept and counted: the
  analysis is intention-to-treat (§4.6.2), so a session cut off at Exemplify
  counts exactly as one that reached Illustrate.
- **Finishing early ends the activity, not the sitting.** A SEE-I participant who
  completes all four steps, or reaches the fallback, sees that they are done and
  is given nothing further, and remains at their station until the period ends
  (§4.6.4).

### The SEE-I group

The ordinary tutoring loop, once. No "Start a new attempt" after it ends, no way
out of the session, and no class label on screen, since a class name could name
the group. A reload picks the session back up. Running out of attempts ends it
like finishing does, without the usual "your instructor has been notified".

### The chatbot group (active control)

A general-purpose chat with **no pedagogical prompt**, on **the same model** and
settings as SENSEE-I's agents (§4.6.2), beside the same reading. Every message is
recorded with its time, as a SEE-I session is.

**The chatbot is not given the reading.** It knows only what the participant
tells it; they may paste text from the reading in themselves. That is what
unguided use looks like, which is what this group stands for. The cost is a
second difference between the two AI groups, which the manuscript should state;
the event log records how many chatbot participants pasted from the reading.

**What it is, exactly:** the same provider, model, temperature and thinking level
as the agents, sent the whole conversation each turn with no system prompt at
all. Its replies are shown the way a general-purpose chatbot shows them, with
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

Every group sees one line of instructions when its reading opens, so no group is
told more than another:

| Group | Says |
| --- | --- |
| SEE-I | The session goes through SEE-I a step at a time; read the whole material first; press Done when finished |
| Chatbot | Read the material; use the chatbot beside it however you like; press Done when finished |
| Reading only | Read the material in its entirety; press Done when finished |

It shows once. A participant who reloads partway does not see it again.

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
answer length, how much an answer changed between attempts, and the fallback rate
per step.

### Added in trial mode: the event log

One row per interaction in `trial_event`, stamped with when it happened by the
participant's browser (and when the server received it). The browser sends what
only it can see in batches every few seconds, and once more as the page closes;
the server records what only it knows. Unknown kinds are refused, and a browser
clock more than an hour out is replaced by the server's.

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
**time running out** is the clock's start plus 40 minutes, and a SEE-I session
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

## Export

A handful of spreadsheet files, all keyed by participant ID: participants (ID,
group, class, sitting), sessions, attempts, criterion judgments, messages, and
events. They open directly in Excel, SPSS, R or Python.

## The order of work

1. **This document.**
2. **The agent gate**, in parallel: few-shot examples and a strict output format
   for the Assessment Agent, then re-run the eval until it reaches 80%.
3. **Trial mode basics:** the setting; class modes; participant IDs, batches and
   ID sign-in; one session per participant, enforced by the server.
4. **The 40 minutes:** the clock from the reading, the countdown, ending by time,
   and counting those sessions in the dashboard.
5. **The control groups:** the chatbot screen and the reading-only screen.
6. **The event log.**
7. **Export, and delete by ID.**
8. **Reliability:** the dropped-connection bug, and abandoned sessions handled the
   trial's way (kept, never deleted).
9. **The trial instance** in `render.yaml`: paid server and database, no automatic
   deploys, pinned to a release.
10. **Stand it up:** release, the instance, a paid Gemini key, the classes and the
    reading.
11. **A dry run** through all three groups, to set the exclusion cut-offs. Then
    wipe the database.
12. **The trial.** The instance stays frozen until the last sitting is done.
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
