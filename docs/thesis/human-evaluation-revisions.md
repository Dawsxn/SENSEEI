# Human evaluation: proposed revisions

For group discussion before updating the manuscript. It collects what came out of
reviewing §4.6–4.7 (the Aug 19 draft, `main (3).pdf`) against how the app will
actually run the trial (`docs/context/trial.md`), and the test design the group
moved to in November: a one-question pre-test, a post-test built on the four
dimensions of conceptual understanding, and ANCOVA. The post-test itself is
planned in more detail in `[SENSEE-I] Post-Test Plan.docx`.

Nothing here is final. Each item says what changes and why, so the group can
accept, adjust, or reject it, then update the manuscript to match.

---

## 1. Decisions to confirm

| # | Decision | Why |
| --- | --- | --- |
| 1 | **The chatbot group is given the reading.** It is a plain chat on the same model, with the reading as its only context and no teaching instructions; participants are told it has the reading | Changed after the user acceptance test, on the adviser's advice: the two AI groups then differ only in guidance (§4.6.2) |
| 2 | **Keep three groups**, including reading-only | Without it, a SENSEE-I win cannot be told apart from the chatbot doing harm. It also tests the cognitive-offloading motivation directly |
| 3 | **Block randomization, prepared before each sitting.** Groups are drawn as shuffled ID slips, equal numbers per group | Random, equal group sizes, no extra time on the day, no names linked to IDs before consent |
| 4 | **The group is not shown on the slip or the consent form** | Participants should take the pre-test not knowing their group, and the consent forms should not double as a list of who was in which group |
| 5 | **Consent is a Google Form, part 1 of the same form as the demographic survey.** It collects name, email and the participant ID; respondents are sent a copy of their responses | One form instead of paper copies on the day, and the emailed copy stands in for the participant's copy. Name and email are removed before analysis, and only the research team can open the responses. Confirm with the DLSU ethics office |
| 6 | **No prior-knowledge screening.** Anyone who volunteers takes part; the demographic survey describes the sample but excludes no one | The pre-test measures what each person already knows, and the analysis adjusts for it, so screening is no longer needed to make the groups start equal |
| 7 | **Pre-test: one question, "Define X"**, X being the reading's concept (a strategic offensive), scored 0–3 with its own anchors | Short, so it does not teach the concept or tire participants before the session, and it measures the starting point the analysis adjusts for |
| 8 | **Post-test: 8 questions on the four dimensions of conceptual understanding** (Mills, 2016), 30 points, all on the general concept: 3 true/false sets of 5 statements on facts and procedures (1 per statement), 2 written questions on connections and 2 short cases on transfer (0–3 each), and a checklist to build, apply and revise on metacognition (0–3). Each question is built so that a known misconception leads to a wrong answer. Never the pre-test question | It measures understanding as the paper defines it, and questions built around misconceptions separate real understanding from recognizing the reading's words. Repeating the pre-test question would reward memorizing one answer. Revised after the user acceptance test, when the earlier multiple choice proved easy to answer without understanding |
| 9 | **Each short-answer item has its own 0–2 anchors**, with a scored example per level. Multiple choice uses an answer key | Each item tests a different dimension, so one shared rubric would not fit all of them |
| 10 | **One grader scores every written answer, blind to the group**, on the grading page of the trial site, which shows participant IDs and never a group | One person grading everything keeps the scoring consistent. With one grader there is no agreement check unless a second person scores a subset (section 6) |
| 11 | **ANCOVA on the post-test, with the pre-test as the covariate**, then pairwise comparisons of the adjusted means with Holm correction | Compares the groups as if they had started level, and with 15 per group it detects smaller differences than a plain ANOVA can |
| 12 | **No alternative test.** If an assumption fails, the analysis still runs as planned and the failure is reported, with its likely effect, as a limitation | Decided in advance, so the choice of test cannot follow the results |
| 13 | **Confidence ticks for calibration, a secondary outcome.** After each of the 11 facts, connections and transfer items, participants tick "I'm sure" or "I'm not sure". Calibration is the share of ticks that match the result (sure and full marks, or not sure and not full marks) | It measures the "examining your own thinking" half of metacognition without a grader, and shows whether a group feels more sure than it should |
| 14 | **The pre-test and post-test are taken in the app**, each with its own timer: pre-test 5 minutes, session 35, post-test 30. Each person moves on as soon as they finish a stage | Nobody waits for a slower group, the times are enforced the same way for everyone, and every answer, tick and timing is recorded with the rest of the data. The times live in the code, so they cannot change between sittings |
| 15 | **The usability survey (SUS) is a Google Form**, reached from a QR code on a slide at the end. Everyone answers a few feedback questions; only participants who used the SEE-I tutor go on to the SUS | No change to the app, and the reading-only and chatbot groups have no SENSEE-I to rate |

---

## 2. The flow

### Before the trial

1. Recruit volunteers from RVRCOB. The announcement says it is voluntary, ungraded, and carries no incentive. It does not name the concept, or people may read up on it.
2. Prepare the consent and demographic Google Form and the feedback and usability Google Form, both asking for the participant ID. The pre-test and post-test are in the app (`backend/trial_tests`); Doc Ben reviews them first, and any change goes in before the first sitting.
3. Upload the reading (strategic offensives, Chapter 6, pp. 109–110, up to the seventh strategy) to the trial instance with the title **Strategic Offensives**, create one class per group with it, and set each class's **Pre-test and post-test** to Strategic Offensives.

### Before each sitting

4. In the app, generate IDs with groups assigned, equal numbers per group.
5. Print slips showing only the ID, plus a few spares, and shuffle them.

### On the day

| # | Step | Where | Time |
| --- | --- | --- | --- |
| 6 | Arrive and set up: check the Wi-Fi, project the QR codes, ready the slips. Participants bring their own laptops | Room | 5:40 to 6:00 |
| 7 | Draw a slip | Paper | 6:00 to 6:20 |
| 8 | Consent, then the demographic survey, in one Google Form starting with the ID (no one is screened out) | Form | (within the 20) |
| 9 | Briefing: open the site on your laptop, keep only that tab open | Room | (within the 20) |
| 10 | Pre-test: "Define X", in the app | App | Up to 5 min |
| 11 | Session: the group's screen opens with the 35-minute countdown | App | Up to 35 min |
| 12 | Post-test: 8 questions with "Is this answer fully correct?" after the first 7, in the app | App | Up to 30 min |
| 13 | Feedback form from the slide's QR code; the SEE-I group also answers the SUS | Form | About 2 to 4 min |

About 6:00 to 7:40, 20 minutes outside the app and up to 70 inside. Participants learn their group only at step 11.

### After each sitting

14. Once everyone has left, close the batch in the app. Its IDs stop working.
15. Keep the consent form's responses where only the research team can open them. They are the only place a name meets an ID.

### After the trial

16. The grader scores every pre-test answer and every post-test written answer on the grading page, by ID, with the group hidden.
17. Export the app data (Download data). With the form responses, everything is keyed by ID.
18. Analyse (section 3).
19. Keep the data two years after the defense, then delete it, including the form responses. A participant who withdraws is deleted by ID.

The dry run uses the same steps. Afterwards, download its data, then delete its batch (Delete batch on the batch's page), which removes every dry-run ID and everything recorded for them.

### Practical notes

- **Google Forms:** the consent and demographic form collects email on purpose, to send each participant a copy. The feedback form does not need it: turn off "Collect email addresses" there and ask for the participant ID first.
- **IDs must not hint at the group** (no `P-S-...` for SENSEE-I), so the grader stays blind.
- **Mix groups within each sitting** and have participants work without talking, so a sitting's conditions are not tied to one group.
- **The app enforces the order:** the reading does not open until the pre-test is in, and the post-test does not open until the session has ended.
- **The post-test instructions ask participants not to mention how they studied the reading**, so the answers do not reveal the group to the grader.

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

- One grader scores every written answer, blind (labelled only by ID), on the trial site's grading page. Multiple choice is scored by the app, and a blank written answer scores 0 automatically.
- Pre-test: 0–3, with its own anchors.
- Post-test: multiple choice by answer key (1 point each); short answers 0–2 with each item's anchors. A participant's post-test score is the total, out of 20.
- Reliability: with one grader, none is measured by default. If a second person scores a random subset, agreement can be checked with weighted kappa (target at least 0.60). Otherwise it is stated as a limitation.
- Dimension scores are described, not tested: too few items per dimension and too few participants per group.

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

### 4. Secondary result: calibration

- Each participant's calibration score is the percentage of their 11 confidence ticks that match the result (decision 13). Computed after grading, with no grader.
- Compare the group averages with a one-way ANOVA, and report each group's count of "sure but wrong" ticks beside it, since that count shows overconfidence most directly.
- Calibration tends to rise with the score, so it is read together with the post-test results.

### 5. Usability

System Usability Scale composite, 0–100: average and spread, against the common benchmark of about 68. Only the SEE-I group takes it (decision 15).

### 6. Process measures (from the app's logs)

- SENSEE-I, described: attempts and time per step, how far each participant got, the fallback rate, criteria failed and then fixed after feedback, and use of the rubric and core-components panels.
- Explored, without causal claims: whether these relate to post-test scores.
- Chatbot group: amount of use, and how many pasted text from the reading.

### 7. Qualitative (decide)

§4.6.2 says understanding is measured "qualitatively and quantitatively", but nothing qualitative is described. Either add a short thematic look at post-test answers or transcripts, or remove "qualitatively".

---

## 4. Manuscript changes, by section

### §4.6.2 Experiment Design

- **Narrow the claim.** "The variable distinguishing the two AI-assisted groups is the SEE-I scaffolding" claims more than the design can show: SENSEE-I also makes students write explanations, gives rubric feedback with retries, and knows the reading. Change to "the SEE-I-based design of SENSEE-I", which matches objective 5, and name what is bundled in the limitations.
- **The chatbot is given the reading** as its only context, with no teaching instructions, and participants are told so. State it in §4.6.2: the AI groups differ only in guidance.
- **The chatbot can search the web**, as a typical chatbot can; its citations are not shown to participants. SENSEE-I cannot search, so state this difference in §4.6.2 alongside the reading. Which replies searched, and which pages they cited, are in the data.
- **The measures change:** a one-question pre-test, and an 8-question post-test on the four dimensions of conceptual understanding (true/false sets, written questions, short cases and a checklist), each built around known misconceptions, with an "Is this answer fully correct?" choice after the first 7.
- **"Qualitatively"**: see analysis item 7.

### §4.6.3 Participants and Sampling

- **Remove the prior-knowledge eligibility criterion.** The pre-test and the covariate take its place.
- **How assignment works:** block randomization within each sitting, so groups are equal in size.
- **The exclusion measures are recorded by the system:** time and turns (SENSEE-I), session length and words typed (chatbot), time before pressing Done (reading-only). Cut-offs are still set from the pilot.

### §4.6.4 Procedure

- **The pre-test is one written question,** taken in the app before the session, with 5 minutes. The reading does not open until it is in.
- **The post-test is 8 questions** covering facts and procedures, connections, transfer and metacognition, with "Is this answer fully correct?" after each of the first 7, taken in the app after the session with 30 minutes and without the reading.
- **The session is 35 minutes, not 40,** enforced by the system from the moment the participant presses Start on the reading's instructions. No countdown is shown (it confused people in the user acceptance test); all three groups get the same pop-ups at 15, 5 and 1 minute left, and the SEE-I group a reminder after 10 minutes of reading. At the limit the session ends and is recorded as ended by time.
- **A briefing comes first, outside the clocks.** Every group sees a welcome screen with the study's aim and its own steps and times. The SEE-I group also reads what SEE-I is and how the session screen works, after the pre-test so the pre-test is not shaped by it. Each stage's instructions name the goal (understanding the concept) and Done asks for confirmation.
- **Each person moves on as soon as they finish a stage.** Every stage's start and end is recorded, and how it ended.
- **Finishing early:** a SENSEE-I participant who completes all four steps, or reaches the fallback, goes straight on to the post-test. One session per participant.
- **The slip is drawn first, then consent**, since the consent form asks for the ID.
- **Participants bring their own laptops**; the room needs Wi-Fi, not a computer lab.

### §4.6.5 Analysis Metrics

Replace with section 3 above. The main changes:

- ANCOVA with the pre-test as the covariate replaces the plain group comparison, with its assumption checks named and the decision to report, not switch, when one fails.
- The post-test is scored out of 20 across the four dimensions, with an answer key for multiple choice and per-item anchors for short answers.
- New: calibration from confidence ticks, as a secondary result.
- One grader scores everything, blind to the group. "Proves objectivity" has to go, since one grader cannot show agreement; state reliability as a limitation unless a subset is double-scored.
- The pre-test becomes a descriptive baseline table, not a significance test.
- "Definitive comparison" is dropped, and the sample-size limitation is stated.
- New: process measures from the app's logs.

### §4.6.6 Data Handling and Retention

- **The system holds no identity.** Participants sign in with their participant ID alone; the only link between an ID and a person is the consent form's responses (name, email and ID), which only the research team can open and which are removed before analysis.
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

1. **What they will do:** on their own laptop, a short question before the session (5 minutes), up to 35 minutes with the reading in one of three set-ups, then a set of questions (30 minutes) and a short survey, ungraded. About 100 minutes in all.
2. **How the set-up is chosen:** at random, by the slip they draw.
3. **What the system records:** answers and the full conversation; time spent; use of the on-screen panels and the reading; when text is pasted (that it happened and its length, never what was pasted); and leaving the browser tab.
4. **How they sign in:** with a participant ID from the slip they draw. The system never asks for or stores their name or email; the consent form does, so a copy can be sent to them and they can withdraw later.
5. **An outside AI service:** answers are sent to Google's Gemini API, on the paid tier.
6. **Retention and withdrawal:** two years after the defense, then deleted; withdrawal at any time, with their record deleted.

Suggested wording:

> You will answer a short question, spend up to 35 minutes with a reading in
> one of three set-ups chosen at random, then answer a set of questions and a
> short survey, all on your own laptop. It takes about 100 minutes and is not
> graded.
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

Check the DLSU research ethics office's consent template first; it may set the format. The manuscript's form (Appendix A) also needs updating: it describes a computer laboratory, only the SENSEE-I procedure, and 85 minutes, and its retention period differs from the ethics checklist's. Pick one retention period and use it everywhere.

---

## 6. Still open

- **The reading's scope:** confirm with Doc Ben that it stops after the seventh offensive strategy, before "Choosing Which Rivals to Attack".
- **Doc Ben's review of the tests:** the 8 questions, the answer key and the rubrics are in `backend/trial_tests/strategic_offensives.yaml`. Changes go in before the first sitting.
- **A source for calibration**, needed once this goes into the manuscript.
- **Who the grader is**, and whether a second person scores a random subset so reliability can be checked.
- **Sittings:** how many, and whether each uses the same reading.
- **Qualitative analysis:** add or drop (analysis item 7).
- **Recruitment scope:** RVRCOB only, or all DLSU undergraduates with the business readings kept. The wider pool would help the small sample.
- **Sample size:** whether more than 45 can be recruited.
