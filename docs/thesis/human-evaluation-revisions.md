# Human evaluation: proposed revisions

For group discussion before updating the manuscript. It collects what came out of
reviewing §4.6–4.7 (the Aug 19 draft, `main (3).pdf`) against how the app will
actually run the trial (`docs/context/trial.md`), and the test design the group
moved to in November: a one-question pre-test, a different post-test, one rubric
for both, and ANCOVA.

Nothing here is final. Each item says what changes and why, so the group can
accept, adjust, or reject it, then update the manuscript to match.

---

## 1. Decisions to confirm

| # | Decision | Why |
| --- | --- | --- |
| 1 | **The chatbot group is not given the reading.** It is a plain chat on the same model; participants may copy text in themselves | It is what unguided use looks like (§2.1). The cost is a second difference between the AI groups, handled in the wording (§4.6.2) |
| 2 | **Keep three groups**, including reading-only | Without it, a SENSEE-I win cannot be told apart from the chatbot doing harm. It also tests the cognitive-offloading motivation directly |
| 3 | **Block randomization, prepared before each sitting.** Groups are drawn as shuffled ID slips, equal numbers per group | Random, equal group sizes, no extra time on the day, no names linked to IDs before consent |
| 4 | **The group is not shown on the slip or the consent form** | Participants should take the pre-test not knowing their group, and the consent forms should not double as a list of who was in which group |
| 5 | **Paper consent forms**, kept separate from the research data | Fits the "two signed copies" wording (§4.6.4) and keeps identity physically apart from the data. Confirm with the DLSU ethics office |
| 6 | **No prior-knowledge screening.** Anyone who volunteers takes part; the demographic survey describes the sample but excludes no one | The pre-test measures what each person already knows, and the analysis adjusts for it, so screening is no longer needed to make the groups start equal |
| 7 | **Pre-test: one question, "Define X"**, X being the reading's concept | Short, so it does not teach the concept or tire participants before the session, and it measures the starting point the analysis adjusts for |
| 8 | **Post-test: two to three different questions** on the same concept, never the pre-test question | Repeating the pre-test question would reward memorizing one answer, and participants could rehearse it with the reading or the chatbot during the session |
| 9 | **One analytic rubric for both tests:** Concept, Application, Reasoning, each 0–3. The pre-test is scored on Concept only | Same yardstick before and after. A definition question gives nothing to judge Application or Reasoning on |
| 10 | **Two graders score every answer, blind**, and each score is the average of the two | Removes the "who grades the rest" gap, and averaging gives finer scores, which the analysis needs |
| 11 | **ANCOVA on the post-test, with the pre-test as the covariate**, then pairwise comparisons of the adjusted means with Holm correction | Compares the groups as if they had started level, and with 15 per group it detects smaller differences than a plain ANOVA can |
| 12 | **No alternative test.** If an assumption fails, the analysis still runs as planned and the failure is reported, with its likely effect, as a limitation | Decided in advance, so the choice of test cannot follow the results |

---

## 2. The flow

### Before the trial

1. Recruit volunteers from RVRCOB. The announcement says it is voluntary, ungraded, and carries no incentive. It does not name the concept, or people may read up on it.
2. Prepare the demographic survey, the pre-test, the post-test, the grading rubric with scored examples, and the usability survey, all keyed by participant ID. Two RVRCOB faculty review the tests first.
3. Pick the reading, upload it to the trial instance, and create one class per group with that reading.

### Before each sitting

4. In the app, generate IDs with groups assigned, equal numbers per group.
5. Print slips showing only the ID, plus a few spares, and shuffle them.

### On the day

| # | Step | Where | Time |
| --- | --- | --- | --- |
| 6 | Consent: read and sign, two copies | Paper | ~5 min |
| 7 | Demographic survey, by ID once drawn (no one is screened out) | Form | (within the 5) |
| 8 | Draw a slip. The researcher writes the ID on both consent copies | Paper | 1 min |
| 9 | Pre-test: "Define X", written, by ID | Form | 5 min |
| 10 | Intervention: sign in to the app with the ID, which opens their group's screen. 40-minute countdown | App | 40 min |
| 11 | Post-test: two to three questions, written, by ID | Form | 20–25 min |
| 12 | Usability survey, by ID (who takes it: see section 6) | Form | 5 min |

About 80 minutes. Participants learn their group only at step 10.

### After each sitting

13. Close that sitting's IDs in the app.
14. Store the consent forms separately and locked. They are the only place a name meets an ID.

### After the trial

15. Export the app data. With the form responses, everything is keyed by ID.
16. Both graders score every pre-test and post-test answer, blind, by ID, with the group hidden.
17. Analyse (section 3).
18. Keep the data two years after the defense, then delete it and destroy the consent forms. A participant who withdraws is deleted by ID.

### Practical notes

- **Google Forms:** turn off "Collect email addresses" and do not restrict the form to DLSU sign-in, or every response records the student's email. Ask for the participant ID as the first question.
- **IDs must not hint at the group** (no `P-S-...` for SENSEE-I), so the graders stay blind.
- **Mix groups within each sitting** and have participants work without talking, so a sitting's conditions are not tied to one group.
- **Collect the pre-test before the session starts**, so it cannot be revised with what the session taught.

---

## 3. The analysis plan (replaces §4.6.5)

### 0. Who is analysed

- Everyone who consents and is given an ID. There is no eligibility screening.
- Exclusions (§4.6.3), from the app's records, with cut-offs set from the dry run:
  - SENSEE-I: total time or number of turns too low.
  - Chatbot: session length or words typed too low.
  - Reading-only: pressed Done too early.
- Everyone else stays in, including unfinished SEE-I sessions (intention-to-treat).

### 1. Scoring

- Two graders score every answer separately and blind (labelled only by ID).
- Pre-test: Concept only, 0–3.
- Post-test: Concept, Application and Reasoning, each 0–3, on each question. A participant's post-test score is the total across the questions (0–18 for two questions, 0–27 for three).
- Final score: the average of the two graders' scores.
- Reliability: weighted kappa per dimension, with a target of at least 0.60. Disagreements of more than one level on a dimension are discussed and settled.

### 2. Baseline description (pre-test)

A table of each group's pre-test scores, average and spread. No significance test: random assignment makes the groups comparable, and ANCOVA adjusts for whatever difference remains.

### 3. Main result: post-test by group (ANCOVA)

- **Model:** post-test score, with group as the factor and pre-test score as the covariate.
- **First, on the raw data, check that the pre-test relates to the post-test the same way in every group** (homogeneity of regression slopes): fit the model with a group × pre-test interaction. If the interaction is not significant, drop it and run the ANCOVA. If it is, report it as a finding, since it means the groups' advantage depends on what a participant already knew.
- **The other assumption checks**, each reported:
  - Linearity: a scatter of post-test against pre-test for each group.
  - Normality of the residuals: Shapiro–Wilk and a Q–Q plot.
  - Equal variances across groups: Levene's test on the residuals.
  - Independence: met by the design (individual work, random assignment, one session each).
- **The overall test:** does group affect the post-test once the pre-test is accounted for?
- **Pairwise comparisons of the adjusted means**, Holm-corrected: SENSEE-I vs. chatbot is the comparison that answers the study's objective; SENSEE-I vs. reading-only and chatbot vs. reading-only give context.
- **Effect sizes** with 95% confidence intervals: partial η² overall, and the adjusted mean difference for each pair.
- **Outliers:** run the analysis with and without them, and report both if the conclusion changes.
- **If an assumption fails:** the analysis is not switched. The failure and its likely effect on the result are reported as a limitation (decision 12).
- **Limitations to state:** with 15 per group only fairly large effects can be detected, though the covariate helps; a non-significant result does not show there is no effect. A single 0–3 pre-test item is a coarse covariate.

### 4. Usability

System Usability Scale composite, 0–100: average and spread, against the common benchmark of about 68. Who takes it is open (section 6).

### 5. Process measures (from the app's logs)

- SENSEE-I, described: attempts and time per step, how far each participant got, the fallback rate, criteria failed and then fixed after feedback, and use of the rubric and core-components panels.
- Explored, without causal claims: whether these relate to post-test scores.
- Chatbot group: amount of use, and how many pasted text from the reading.

### 6. Qualitative (decide)

§4.6.2 says understanding is measured "qualitatively and quantitatively", but nothing qualitative is described. Either add a short thematic look at post-test answers or transcripts, or remove "qualitatively".

---

## 4. Manuscript changes, by section

### §4.6.2 Experiment Design

- **Narrow the claim.** "The variable distinguishing the two AI-assisted groups is the SEE-I scaffolding" claims more than the design can show: SENSEE-I also makes students write explanations, gives rubric feedback with retries, and knows the reading. Change to "the SEE-I-based design of SENSEE-I", which matches objective 5, and name what is bundled in the limitations.
- **The chatbot is not given the reading.** State it, and either justify it as part of unguided use or note it as a limitation. The app records how many chatbot participants pasted text from the reading.
- **The measures change:** a one-question pre-test and a two-to-three-question post-test, scored with one analytic rubric.
- **"Qualitatively"**: see analysis item 6.

### §4.6.3 Participants and Sampling

- **Remove the prior-knowledge eligibility criterion.** The pre-test and the covariate take its place.
- **How assignment works:** block randomization within each sitting, so groups are equal in size.
- **The exclusion measures are recorded by the system:** time and turns (SENSEE-I), session length and words typed (chatbot), time before pressing Done (reading-only). Cut-offs are still set from the pilot.

### §4.6.4 Procedure

- **The pre-test is one written question,** taken before the session and collected before it starts.
- **The post-test is two to three different questions** on the same concept, written.
- **The 40 minutes are enforced by the system**, from the moment the reading opens, with a countdown visible to all three groups. At the limit the session ends and is recorded as ended by time.
- **Finishing early:** a SENSEE-I participant who completes all four steps, or reaches the fallback, is shown they are done and given nothing further. One session per participant.
- **The ID is drawn after consent**, and written on both consent copies.

### §4.6.5 Analysis Metrics

Replace with section 3 above. The main changes:

- ANCOVA with the pre-test as the covariate replaces the plain group comparison, with its assumption checks named and the decision to report, not switch, when one fails.
- One analytic rubric scores both tests; the pre-test on Concept only.
- Two graders score everything, scores are averaged, and agreement uses weighted kappa with a stated target. "Proves objectivity" becomes "establishes reliability".
- The pre-test becomes a descriptive baseline table, not a significance test.
- "Definitive comparison" is dropped, and the sample-size limitation is stated.
- New: process measures from the app's logs.

### §4.6.6 Data Handling and Retention

- **The system holds no identity.** Participants sign in with their participant ID alone; the only link between an ID and a person is the paper consent form.
- **Interaction logs** join the list of performance records: timing, panel use, reading navigation, paste events (length only, never content), and tab switches.
- **External processing.** Responses are sent to Google's Gemini API to be graded and to produce replies, on the paid tier, whose terms do not allow Google to use the content to improve its products. Check the current terms before the trial. The manuscript does not mention this yet.
- **Where the data lives.** The trial runs on a separate instance used only for the study. After the last sitting its data is exported to secure storage, restricted to the research team, and the instance is shut down. Retention and deletion apply to that export.

### §4.7.3 Privacy and Confidentiality

- "For research analysis **and instructor review**": only the research team has instructor access on the trial instance, and §4.6.3 promises no instructor learns who took part. Remove "instructor review", or say the instructors are the researchers.

### §4.7.4 Protection and Responsible Use of Research Data

- "Handled separately from research data **where applicable**": with ID-only sign-in it always applies. State it plainly.

### §5.4 Limitations (correction)

- "State accounted for 4 of the 18 errors" should read **4 of the 11 errors**. There were 11 parse errors in total; the 22.2% is right, as 4 of State's 18 examples.

---

## 5. Consent form

Informed consent means telling participants what is collected about them. The form should cover:

1. **What they will do:** a short written question before the session, 40 minutes with the reading in one of three set-ups, then a few written questions and a short survey. About 80 minutes in all, ungraded.
2. **How the set-up is chosen:** at random, by the slip they draw.
3. **What the system records:** answers and the full conversation; time spent; use of the on-screen panels and the reading; when text is pasted (that it happened and its length, never what was pasted); and leaving the browser tab.
4. **How they sign in:** with a participant ID given to them at consent. The system never asks for or stores their name or email.
5. **An outside AI service:** answers are sent to Google's Gemini API, on the paid tier.
6. **Retention and withdrawal:** two years after the defense, then deleted; withdrawal at any time, with their record deleted.

Suggested wording:

> You will answer a short written question, spend 40 minutes with a reading in
> one of three set-ups chosen at random, then answer a few more written questions
> and a short survey. It takes about 80 minutes and is not graded.
>
> During the session you will use a computer program. It records your answers,
> the conversation with the program, the time you spend, and how you use the
> on-screen panels and the reading, including when you paste text (but not what
> you paste) and when you leave the window. You will sign in with a participant
> ID, not your name, and the program does not store your name or email.
>
> Your answers are sent to an external AI service (Google Gemini) to generate
> replies and feedback. Under its terms for the paid service used in this study,
> your answers are not used to train or improve Google's products.
>
> Your data is kept for two years after the study is defended and then deleted.
> You may withdraw at any time, and your data will be deleted.

Check the DLSU research ethics office's consent template first; it may set the format.

---

## 6. Still open

- **The reading and the concept X:** which reading, and so which concept the pre-test asks about. The app needs it before the dry run.
- **The post-test questions:** written by the group, possibly reviewed by Doc Ben, and whether there are two or three.
- **The rubric's anchors:** what earns 0, 1, 2 and 3 on each dimension, with a few scored examples so the graders calibrate.
- **Who the graders are:** the two RVRCOB professors, as before, or others.
- **Who takes the usability survey:** SENSEE-I only, or both AI groups. The reading-only group has no system to rate.
- **Sittings:** how many, and whether each uses the same reading.
- **Qualitative analysis:** add or drop (analysis item 6).
- **Recruitment scope:** RVRCOB only, or all DLSU undergraduates with the business readings kept. The wider pool would help the small sample.
- **Sample size:** whether more than 45 can be recruited.
