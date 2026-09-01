# Trial content

The expository text the trial runs on. Drop it here as `reading.txt` (or any
name) and point `reading.path` in [`../trial.yaml`](../trial.yaml) at it.

All three arms receive the same text (§4.6.2). The harness serves it directly to
the passive and unguided arms; the SENSEE-I arm receives it through the
application's own reading upload. **Those are two copies of one document**, so
upload the same file rather than re-extracting it from the source, and let the
pre-flight checksum confirm they match. A silently divergent copy would confound
every comparison the study makes without anything appearing to go wrong.

Plain UTF-8 text. Whatever the participants read is what is stored here, so a
formatting change is a change to the stimulus and belongs in a commit.

## Choosing the text

Two constraints decide it together:

- §4.6.3 requires participants who have **not previously studied the concept** it
  covers, verified by the familiarity screening before the pre-test. A text on a
  concept most RVRCOB students have already met would disqualify the cohort.
- The pre-test, post-test Part A, and the SBA case are all built against this
  text and reviewed for content validity by two faculty (§4.6.4). Changing the
  reading after that review means redoing it.

Three candidate business-concept readings already exist in the eval harness
(`assessment-agent-eval/data/readings/`: strategy, business model, strategic
vision), drawn from Gamble et al.'s *Essentials of Strategic Management*. They
were built for grading the Assessment Agent rather than for the trial, so treat
them as candidates, not defaults — and check the licensing position before
putting a textbook extract in front of 45 participants.
