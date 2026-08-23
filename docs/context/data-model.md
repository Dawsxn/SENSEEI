# Data model

Entities, relationships, and the constraints that come from how the system is
meant to behave.

The manuscript names what is stored (readings, core components, sessions,
responses, assessments, classes) but specifies no schema. Everything below is a
proposal.

## How it fits together

In plain terms, reading down the chain:

**An instructor creates a class.** The class gets a join code. Students enter that
code to enrol. Enrolment is the only thing that decides what a student can see.

**The instructor uploads a reading** and, at upload time, types in its core
components: the essential defining parts of the concept that reading covers. They
also pick which classes the reading is assigned to. A student sees a reading only
if one of their classes has it assigned.

**A student opens a reading and starts a session.** One session is one full pass
through the four SEE-I steps for that one reading. The session row tracks which
step they are on and whether it is still running, finished, or ended in fallback.

**Within a session, each thing the student types is an attempt.** An attempt
belongs to a session and records which step it was for and which try it was, so
the first try at Elaborate and the third try at Elaborate are two rows that both
point at the same session.

**Every attempt gets graded, and that grade is an assessment.** One attempt, one
assessment. The assessment holds the overall verdict and the bookkeeping around
the model call.

**The assessment breaks down into criterion judgments**, one row per rubric
criterion the agent looked at, each saying whether it passed and why. This is the
finest-grained thing stored, and it is what the instructor analytics count.

**Separately, the chat itself is stored as tutor messages**, so the transcript can
be replayed exactly as the student saw it.

The reason the chain goes session, attempt, assessment, criterion judgment
instead of collapsing into fewer tables is that the instructor dashboard asks
questions at each level: how many students finished (session), how many tries do
they need on average (attempt), what is the pass rate per step (assessment), and
which criteria do they fail most (criterion judgment). Each level has a consumer.

## Shape

```mermaid
erDiagram
    USER ||--o{ ENROLMENT : "enrols via"
    USER ||--o{ CLASS : teaches
    USER ||--o{ READING : uploads
    USER ||--o{ SESSION : works_through

    CLASS ||--o{ ENROLMENT : has
    CLASS ||--o{ READING_ASSIGNMENT : "is assigned"

    READING ||--o{ CORE_COMPONENT : defines
    READING ||--o{ READING_ASSIGNMENT : "assigned to"
    READING ||--o{ SESSION : "studied in"

    SESSION ||--o{ ATTEMPT : contains
    SESSION ||--o{ TUTOR_MESSAGE : transcript

    ATTEMPT ||--|| ASSESSMENT : graded_by
    ASSESSMENT ||--o{ CRITERION_JUDGMENT : breaks_down
```

## Entities

### user

One table for both roles. A user is either an instructor or a student, never
both.

| Field | Notes |
| --- | --- |
| id | |
| role | student or instructor |
| name | |
| email | |
| google_sub | Google account subject, the stable identifier from sign-in |
| participant_identifier | Null for ordinary users. Set for consented study participants, see [Pseudonymisation](#pseudonymisation) |
| created_at | |

Sign-in is Google OAuth, restricted to DLSU addresses. A non-DLSU Google account
cannot sign in at all, so enrolment is not the only gate.

### class

| Field | Notes |
| --- | --- |
| id | |
| instructor_id | Exactly one. Co-teaching is not supported |
| name | |
| join_code | Generated on creation. Students enrol with it (§4.3.4) |
| created_at | |

### enrolment

Join table between student and class. Enrolment decides which readings a student
can see (§4.3.4).

| Field | Notes |
| --- | --- |
| student_id | |
| class_id | |
| enrolled_at | |

### reading

| Field | Notes |
| --- | --- |
| id | |
| uploaded_by | Instructor |
| title | |
| source_file | The original upload, retained |
| content | Extracted plain text. This is what the agents receive |
| created_at | |

Both the original file and the extracted text are kept. The agents only ever see
`content`, but retaining the source means a bad extraction can be re-run later
without asking the instructor to upload again.

### core_component

One or more per reading. The essential defining parts of the concept.

| Field | Notes |
| --- | --- |
| id | |
| reading_id | |
| text | |
| position | Display order |

**Immutable after upload.** An instructor may not change a reading's core
components once uploaded, because doing so would invalidate the results and
statistics of prior sessions on that reading (§4.3.4). Enforce this in code, not
by convention.

### reading_assignment

Which classes a reading is assigned to.

| Field | Notes |
| --- | --- |
| reading_id | |
| class_id | |

**Mutable**, unlike core components. Assignment only affects who can see a
reading, not its content, so instructors can change it freely after upload
(§4.3.4).

### session

One complete pass through the four SEE-I steps for one reading.

| Field | Notes |
| --- | --- |
| id | |
| student_id | |
| reading_id | |
| status | in_progress, complete, or fallback |
| current_step | State, Elaborate, Exemplify, or Illustrate |
| started_at | |
| ended_at | Null while in progress |
| rubric_version | The rubric this session was graded under |
| prompt_version | The agent prompts used |
| model | The LLM that graded it |

The last three exist so a session stays interpretable after the rubric or prompts
change. The eval harness already pins and stamps these on every run; sessions
need the same discipline, otherwise a rubric revision silently changes the
meaning of historical pass rates.

Sessions are not resumable. A student who leaves mid-session confirms that it
will be discarded, and the row is discarded with it. Nothing in `in_progress`
survives the student walking away.

A session with `status = fallback` is what raises the instructor's roster flag.
The flag belongs to the session, not to the student: it is a fact about one
session that ended a particular way, derived from `status` rather than stored.
It is not dismissible. A student with three fallback sessions on a reading has
three of them, and clearing one would mean editing the record of what happened.

Students can view all of their past sessions for a reading, not only the most
recent.

### attempt

One student response to one step. A step can have several.

| Field | Notes |
| --- | --- |
| id | |
| session_id | |
| step | |
| attempt_number | 1-based, resets per step |
| response_text | |
| submitted_at | |

Attempts are rows rather than a counter because §4.3.6 requires the average
number of attempts students need to pass each step, and because the instructor
transcript view shows the student's reasoning chain, which means every attempt
has to survive.

A failed provider call must not create an attempt row. See open question 3 in
`agent-contracts.md`.

### assessment

The Assessment Agent's judgment of one attempt. One to one with attempt.

| Field | Notes |
| --- | --- |
| id | |
| attempt_id | |
| verdict | PASS or FAIL, derived in code |
| model_verdict | What the model stated, kept as a cross-check |
| raw_response | The model's justification |
| warnings | Parse warnings, hallucinated or missing criteria |
| usage | Token counts |
| created_at | |

`verdict` and `model_verdict` are stored separately on purpose. A disagreement
between them is a signal worth keeping rather than collapsing.

### criterion_judgment

One row per criterion the agent judged.

| Field | Notes |
| --- | --- |
| id | |
| assessment_id | |
| criterion | Criterion name, canonical form |
| passed | |
| reason | |

Rows rather than a JSON blob because §4.3.6 requires the most frequently failed
criteria across a class, which is a query over this table.

### tutor_message

The chat transcript.

| Field | Notes |
| --- | --- |
| id | |
| session_id | |
| step | |
| attempt_id | Null for an opening Prompt |
| moves | Which dialogue moves this message composed |
| content | What the student saw |
| created_at | |

Storing `moves` makes it possible to check later that the Tutor Agent behaved as
specified, and to reconstruct the transcript without re-inferring intent from
prose.

## What the analytics need

§4.3.6 specifies three class-wide statistics, narrowable to a single reading.
Each maps onto the schema:

| Statistic | Query over |
| --- | --- |
| Pass rate per SEE-I step | attempt joined to assessment, grouped by step |
| Most frequently failed criteria | criterion_judgment where passed is false |
| Average attempts to pass each step | attempt, max attempt_number per session and step |

If a schema change makes any of these three awkward, the schema is wrong.

## Retention and privacy

Two separate regimes. Do not conflate them.

### Study data

Binding, from the manuscript (§4.6.6, §4.7.1, §4.7.4). These apply to data
collected from human participants during the experiment:

1. **Participants are pseudonymised.** Each is assigned a randomly generated
   participant identifier at consent, and all performance records including
   session transcripts are keyed to that identifier rather than to their
   identity.
2. **Identifiers are held separately from research data** where applicable.
3. **Data is deleted at the end of the retention period**, along with consent
   forms. Nothing is kept beyond the study.
4. **A withdrawing participant's record is deleted** before the end of that
   period, at any point they ask.

Points 3 and 4 mean deletion cannot be an afterthought. Deleting one student has
to remove their sessions, attempts, assessments, criterion judgments, and
messages, which the cascade above supports but only if foreign keys are declared
with that in mind. Build the delete path early; retrofitting it is painful.

### App data

The app is meant to run long term, not only for the duration of the experiment.
Ordinary data is not on a deletion clock: sessions, attempts, and transcripts
persist for as long as the account and the class exist, because a student
reviewing last term's sessions and an instructor comparing this year's cohort to
last year's both depend on that.

The study rules above apply to the subset of users who consented to participate,
not to the app's users at large.

That subset has to be identifiable, otherwise the study deletion in point 3
cannot be carried out without destroying app data belonging to everyone else.
The `participant_identifier` field on `user` does this job: null for an ordinary
user, set for a consented participant.

## Pseudonymisation

Replacing someone's identity with a meaningless code, so their data can be
analysed without revealing who they are. Participant `P-047` rather than a name
and an email. It differs from anonymisation in being reversible: the link back to
the person still exists, held separately and access-controlled, which is what
lets a participant withdraw later and have their record found and deleted.

The manuscript requires it for study data (§4.6.6): every participant is assigned
a random identifier at consent, and performance records are keyed to it rather
than to their identity.

How this fits an app that also needs real identities for its own features:

| Context | Uses |
| --- | --- |
| The app itself | Real identity. The instructor roster is unusable without names |
| Research exports | The participant identifier, with name and email dropped |

So the identifier is stored on the user row, and the substitution happens when
research data is exported. Storing it rather than generating it per export means
the same participant maps to the same code every time, so two exports can be
compared.

## Open questions

| # | Question | Blocks |
| --- | --- | --- |
| 1 | Which upload formats are supported beyond PDF? Recommendation below | Upload flow, reading table |

**On question 1.** PDF plus a paste-as-text option covers nearly everything at
low cost, and DOCX can follow if instructors ask. Whatever the format, recommend
showing the instructor the extracted text before the reading goes live, with the
option to correct it. Extraction is lossy, that text is what every agent grades
against, and a mangled extraction would silently poison every session on that
reading.

## Related

- `docs/context/student-tutoring-loop.md`, the behaviour this stores
- `docs/context/agent-contracts.md`, what produces assessments
