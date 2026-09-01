# Runbook

How to actually use the harness, in the order you will need it.

[README.md](README.md) explains why it is built the way it is. This is what you
do.

---

## 1. Install and start

```bash
pip install -e ".[study]"
python -m uvicorn study.api.app:app --reload
```

Open <http://127.0.0.1:8000>. That is the **proctor console**.

The console opens with a banner listing everything that would stop this being
real collection. Read it. It is the same list a fresh clone shows, and it shrinks
as you complete the steps below. Nobody should ever have to guess whether they
are looking at a rehearsal or the real thing.

The three screens:

| URL | Who opens it |
| --- | --- |
| `/` | The proctor |
| `/p/<code>` | One participant, for their whole session |
| `/rate/<rater>` | A faculty rater, after collection |
| `/agreement` | The research team, after grading |

---

## 2. Set up a trial

Everything pinned for one run lives in [`trial.yaml`](trial.yaml).

### 2.1 The reading

Put the expository text in `study/content/` and point at it:

```yaml
reading:
  path: content/your-reading.txt
  title: "Switching Costs"
  core_components: []
```

Plain UTF-8. All three arms get this text — the harness serves it to the passive
and unguided arms directly, and the SENSEE-I arm receives it through the
application's own reading upload. **Upload the same file**, do not re-extract it,
or the arms are reading two documents.

The sample reading ships with a marker on its first line and the pre-flight
refuses a live run while that marker is present. Replace it; do not edit around
it.

### 2.2 The three lines that must be set

```yaml
trial_id: "pilot-2026-10"      # keys the export
allocation_seed: 20261015      # WRITE THIS DOWN
senseei_base_url: "https://senseei-app.example"
dry_run: false                 # last, once everything else is ready
```

**The seed is the one to be careful with.** It is what lets anyone re-derive the
arm assignment afterwards and confirm nobody adjusted it mid-study. Choose it
deliberately, record it outside this file, and never change it once a
participant has been checked in.

### 2.3 The model

```yaml
llm:
  provider: gemini
  model: gemini-3.1-pro-preview
  api_key_env: GEMINI_API_KEY
```

Put the key in `.env` at the repository root. §4.6.2 requires the unguided arm to
run the same model as SENSEE-I's agents, so this must match whatever the
application runs — `assert_model_parity` checks it and refuses when it cannot.

Switching model or provider is this block and nothing else. No code changes.

### 2.4 The database

```bash
export STUDY_DATABASE_URL="postgresql+psycopg://user:pass@host/senseei_study"
```

The default is a local SQLite file, which is right for development and **wrong
for the lab**: on Render or Railway a container filesystem does not survive a
redeploy. Set this before a real sitting.

---

## 3. Write the instruments

Five surveys in [`instruments/content/`](instruments/content/). Demographics and
the SUS are done. Three are stubs, because every item in them is about the
concept your reading covers:

| File | What goes in it |
| --- | --- |
| `pre_test.yaml` | Likert familiarity ratings (mark `screening: true`) and factual items |
| `post_test_a.yaml` | The factual items' partners, each with `pairs_with` |
| `sba.yaml` | The business case in `stimulus`, the question as a `long_text` item |

Each stub's comments carry the manuscript's requirements. **Write the pre-test
and post-test A together** — the post-test items answer the pre-test items, and
that pairing is what makes retention measurable.

A complete worked set against the sample reading is in
[`instruments/example/`](instruments/example/). Copy its shape.

```bash
python -m study.instruments.review --example   # see a finished set
```

Embed at least one attention check in the pre-test and one in post-test A, with
`attention_check.expected` naming the option an attentive person picks.

**The loader will refuse** an attention check whose expected answer is not among
its options, a scored item whose answer is not among its options, a `pairs_with`
that does not resolve, or a duplicate item id. Those all produce data that looks
fine and means nothing, so they fail loudly instead.

### Faculty review (§4.6.4)

```bash
python -m study.instruments.review
```

Writes `review.html`. Send that to your two RVRCOB faculty. It is generated from
the same YAML the tool serves, so it cannot drift from what participants sit, and
it shows reviewers the correct answers, attention checks, and pairings that
participants never see.

When they sign off, set `status: reviewed` in each file. The pre-flight refuses a
live run while any instrument is a draft.

---

## 4. Run a pilot

**Not optional.** §4.6.3's exclusion thresholds are "empirically derived prior to
the main data collection phase" — that means from the pilot. Without it the
exclusion criteria have no numbers you can defend.

Six participants, two per arm, is enough. Use a separate `trial_id` and a
separate database; pilot data is not analysed with the main data.

Afterwards, export and look at the distributions:

```bash
python -m study.export pilot-export
```

`participants.csv` gives you session times, turn counts, words typed, and time on
text. The console also shows running medians during the run. Decide your cutoffs
from those, write them into the manuscript, and apply them at analysis — **not in
the code**. A threshold compiled into the tool could not be revised later without
invalidating everything collected under the old one.

---

## 5. Collection day

### Before anyone arrives

1. `git tag` the code and deploy that tag. **No deploys between the first and
   last participant**, or your arms ran on different software.
2. Set `dry_run: false` and confirm the console's banner is empty.
3. Check the provider quota. One sitting puts 30 participants on the model at
   once for 40 minutes; a 429 storm cannot be re-run.
4. Print the instruments. If the network fails mid-session, an SBA on paper is
   recoverable and a lost one is not.
5. Have the signed consent forms to hand, serial-numbered.

### Checking someone in

Consent is signed **on paper first** — the participant keeps one copy, you keep
the second (§4.6.4). Then on the console: enter their name and the form's serial,
and press *Check in & assign*.

The console assigns their arm from the pre-generated allocation — you do not
choose it — and hands you their link, `/p/<code>`. Give them the link. They need
nothing else; the page always shows whatever phase they are in.

Their name goes in a separate table from their responses and never reaches the
export.

### During the session

Watch the roster. The **Engagement measures** panel shows the §4.6.3 quantities
live, with running medians.

A **highlighted row** means a measure is sitting at zero, or an incident is
logged, or a tool failed to start. That almost always means something is broken
— an unguided participant with no turns twenty minutes in is far more likely
looking at a failed model connection than being idle. Fix broken tools.

**Do not act on low engagement.** Nudging someone to engage more is an
intervention, and an unblinded one. Fix tools; leave participants alone.

Use the incident box to log anything unusual against a participant. It reaches
the export.

Participants who finish early continue straight on — nobody waits for the room.
A participant still working at 40:00 is moved on automatically, and their record
is flagged as having run out of time, which is not the same as low engagement.

### If the server restarts

Nothing is lost. Participants resume where they were, and the intervention clock
keeps running rather than granting a fresh forty minutes. Their existing links
still work.

### If someone withdraws (§4.7.1)

`POST /participants/<id>/withdraw`, or the console's control. It deletes their
research record, their identity, and asks the application to delete their session.
Not reversible — a withdrawal that left the data recoverable would not be one.

---

## 6. After collection

### Export

```bash
python -m study.export analysis
python -m study.export analysis --raters rater-a,rater-b
```

The first writes the **analysis bundle**:

| File | Feeds |
| --- | --- |
| `participants.csv` | Arm, §4.6.3 measures, attention checks, SUS |
| `instrument_scores.csv` | The pre-test and post-test A ANOVAs |
| `instrument_answers.csv` | Item analysis, the paired retention comparison |
| `phase_durations.csv` | Time-on-task, which now varies between participants |
| `sba_responses.csv` | The primary outcome, arm attached |
| `unguided_transcripts.csv` | What unguided use actually looked like |
| `passive_reading.csv` | Time on text, scroll depth |
| `senseei_sessions.csv` | Steps, attempts, failed criteria, rubric/prompt/model versions |
| `manifest.json` | Provenance: seed, model, reading checksum, counts |

Everything is keyed to `participant_id`. No file contains a name.

The second writes the **blind grading bundle**: one file per rater with SBA text
under a blind key, shuffled per rater, plus `rater_key.csv` mapping keys back to
participants. **`rater_key.csv` is for the research team only.** Giving it to a
rater undoes the blinding.

### Grading (§4.6.5)

Send each faculty rater their link, `/rate/rater-a` and `/rate/rater-b`. They see
one response at a time, in their own order, with no arm and no participant id,
and score the three Table 4.12 dimensions.

Then open `/agreement`:

- **Cohen's Kappa per dimension** — this is what §4.6.5 asks you to report.
- **Weighted Kappa** beside it, because unweighted counts
  Developing-vs-Proficient as the same failure as Beginning-vs-Proficient.
- **Disagreements**, widest gap first, as the agenda for the consensus
  discussion.

If Kappa reads **undefined**, both raters used a single category throughout.
That is not perfect agreement — chance agreement is already total and there is no
room above it to measure. Do not report it as 1.0.

### End of retention (§4.6.6)

Two years after the defence, `Repository.delete_everything()` clears every table,
and the signed consent forms are destroyed separately.

---

## Troubleshooting

**"The unguided arm cannot reach a model"** — the provider SDK is not installed
or the API key is missing. `pip install -e ".[gemini]"` and check `.env`. The
other two arms still run.

**"Instruments not ready"** — a stub has no content, or has not been marked
`status: reviewed`.

**"The reading ... is still the sample text"** — replace `content/reading.sample.txt`.

**"allocation_seed is unset"** — set it, and write it down.

**A participant's page shows "tool failed"** — their arm's tool could not start.
This is a technical failure, recorded separately from engagement so it is never
read as a disengaged participant. Fix it and tell them it was not their doing.

**Kappa says "undefined"** — see above. It is not 1.0.

---

## Running the tests

```bash
python -m pytest study/tests -q
```

Run these after changing anything. The randomisation, the intervention deadline,
and the round trip through storage are the three that fail silently in ways the
data would not show.
