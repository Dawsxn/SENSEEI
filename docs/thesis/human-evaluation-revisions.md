# Human evaluation: proposed revisions

For group discussion before updating the manuscript. It collects what came out of
reviewing §4.6–4.7 (the Aug 19 draft, `main (3).pdf`) against how the app will
actually run the trial (`docs/context/trial.md`).

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
| 6 | **Eligibility is screened in the demographic survey on the day**, with a light general check at recruitment | As §4.6.3–4.6.4 already say. Do not name the concept at recruitment, or people may read up on it |
| 7 | **No covariate.** Compare groups on the SBA directly | Screening removes concept-knowledge head starts, and a concept pre-test would mostly score near zero. Random assignment makes the direct comparison valid |
| 8 | **Both RVRCOB professors grade all 45 SBA answers**, and the final score is the average of the two | Removes the "who grades the rest" gap, and averaging gives finer scores, which the analysis needs |
| 9 | **One-way ANOVA, then Tukey** for the pairwise comparisons | Simple and standard. SENSEE-I vs. chatbot is named as the comparison that answers the objective |

---

## 2. The flow

### Before the trial

1. Recruit volunteers from RVRCOB. The announcement says it is voluntary, ungraded, and carries no incentive.
2. Light check at sign-up: which business courses they have taken, without naming the concept.
3. Prepare the pre-test, Part A, the SBA case, and the usability survey, all keyed by participant ID. Two RVRCOB faculty review the tests and the case first.

### Before each sitting

4. In the app, generate IDs with groups assigned, equal numbers per group.
5. Print slips showing only the ID, plus a few spares, and shuffle them.

### On the day

| # | Step | Where | Time |
| --- | --- | --- | --- |
| 6 | Consent: read and sign, two copies | Paper | ~5 min |
| 7 | Eligibility: demographic survey. Ineligible participants stop here | Form | (within the 5) |
| 8 | Draw a slip. The researcher writes the ID on both consent copies | Paper | 1 min |
| 9 | Pre-test: familiarity ratings and factual items, by ID | Form | 5 min |
| 10 | Intervention: sign in to the app with the ID, which opens their group's screen. 40-minute countdown | App | 40 min |
| 11 | Post-test Part A: multiple choice, by ID | Form | 10 min |
| 12 | Post-test Part B: the SBA case, written, by ID | Form | 20 min |
| 13 | Usability survey (SENSEE-I group only), by ID | Form | 5 min |

About 85 minutes. Participants learn their group only at step 10.

### After each sitting

14. Close that sitting's IDs in the app.
15. Store the consent forms separately and locked. They are the only place a name meets an ID.

### After the trial

16. Export the app data. With the form responses, everything is keyed by ID.
17. Both professors grade all 45 SBA answers, blind, by ID.
18. Analyse (section 3).
19. Keep the data two years after the defense, then delete it and destroy the consent forms. A participant who withdraws is deleted by ID.

### Practical notes

- **Google Forms:** turn off "Collect email addresses" and do not restrict the form to DLSU sign-in, or every response records the student's email. Ask for the participant ID as the first question.
- **IDs must not hint at the group** (no `P-S-...` for SENSEE-I), so the graders stay blind.
- **Mix groups within each sitting** and have participants work without talking, so a sitting's conditions are not tied to one group.

---

## 3. The analysis plan (replaces §4.6.5)

### 0. Who is analysed

- Eligibility is screened in the demographic survey; ineligible people never receive an ID.
- Exclusions (§4.6.3), from the app's records, with cut-offs set from the dry run:
  - SENSEE-I: total time or number of turns too low.
  - Chatbot: session length or words typed too low.
  - Reading-only: pressed Done too early.
  - Anyone: failed an attention check.
- Everyone else stays in, including unfinished SEE-I sessions (intention-to-treat).

### 1. Baseline description (pre-test)

A table of each group's pre-test results, average and spread. No significance test: random assignment makes the groups comparable, and the table shows readers they started similar.

### 2. Factual recall (Part A)

- One-way ANOVA across the three groups, then Tukey to see which differ.
- Fallback if not roughly normal: Kruskal–Wallis, then Dunn's tests with Holm correction.
- Also describe each group's pre-to-post change on the paired items.

### 3. Scoring the SBA

- Both RVRCOB professors grade all 45 answers, separately and blind (labelled only by ID).
- Each answer is rated 1–3 on Concept Retrieval, Scenario Application, and Analytical Justification, for a total of 3–9.
- Final score: the average of the two graders' totals.
- Reliability: weighted kappa per dimension, with a target of at least 0.60. Disagreements of more than one level on a dimension are discussed and settled.

### 4. Main result: SBA by group

- One-way ANOVA: does at least one group differ?
- Tukey post-hoc tests: which pairs differ. Use Games–Howell instead if the groups' spreads differ.
- SENSEE-I vs. chatbot is the comparison that answers the study's objective; the other two give context.
- Effect sizes with 95% confidence intervals: η² overall, Hedges' g for each pair.
- Assumption checks: Shapiro–Wilk (normality) and Levene's (equal variances).
- Fallback, stated in advance: Kruskal–Wallis, then Dunn's tests with Holm correction.
- Limitation: with 15 per group, only large effects (roughly f ≥ 0.48) can be detected reliably. A non-significant result does not show there is no effect.

### 5. Usability (SENSEE-I only)

System Usability Scale composite, 0–100: average and spread, against the common benchmark of about 68.

### 6. Process measures (from the app's logs)

- SENSEE-I, described: attempts and time per step, how far each participant got, the fallback rate, criteria failed and then fixed after feedback, and use of the rubric and core-components panels.
- Explored, without causal claims: whether these relate to SBA scores.
- Chatbot group: amount of use, and how many pasted text from the reading.

### 7. Qualitative (decide)

§4.6.2 says understanding is measured "qualitatively and quantitatively", but nothing qualitative is described. Either add a short thematic look at SBA answers or transcripts, or remove "qualitatively".

---

## 4. Manuscript changes, by section

### §4.6.2 Experiment Design

- **Narrow the claim.** "The variable distinguishing the two AI-assisted groups is the SEE-I scaffolding" claims more than the design can show: SENSEE-I also makes students write explanations, gives rubric feedback with retries, and knows the reading. Change to "the SEE-I-based design of SENSEE-I", which matches objective 5, and name what is bundled in the limitations.
- **The chatbot is not given the reading.** State it, and either justify it as part of unguided use or note it as a limitation. The app records how many chatbot participants pasted text from the reading.
- **"Qualitatively"**: see analysis item 7.

### §4.6.3 Participants and Sampling

- **How assignment works:** block randomization within each sitting, so groups are equal in size.
- **The exclusion measures are recorded by the system:** time and turns (SENSEE-I), session length and words typed (chatbot), time before pressing Done (reading-only). Cut-offs are still set from the pilot.

### §4.6.4 Procedure

- **The 40 minutes are enforced by the system**, from the moment the reading opens, with a countdown visible to all three groups. At the limit the session ends and is recorded as ended by time.
- **Finishing early:** a SENSEE-I participant who completes all four steps, or reaches the fallback, is shown they are done and given nothing further. One session per participant.
- **The ID is drawn after consent and eligibility**, and written on both consent copies.

### §4.6.5 Analysis Metrics

Replace with section 3 above. The main changes:

- The baseline ANOVA becomes a descriptive table.
- Part A gets a named test, and "retention" becomes "recall".
- Both professors grade everything, scores are averaged, and agreement uses weighted kappa with a stated target. "Proves objectivity" becomes "establishes reliability".
- The main analysis names its post-hoc test, effect sizes, assumption checks, fallback, and the sample-size limitation. "Definitive comparison" is dropped.
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

1. **What the system records:** answers and the full conversation; time spent; use of the on-screen panels and the reading; when text is pasted (that it happened and its length, never what was pasted); and leaving the browser tab.
2. **How they sign in:** with a participant ID given to them at consent. The system never asks for or stores their name or email.
3. **An outside AI service:** answers are sent to Google's Gemini API, on the paid tier.
4. **Retention and withdrawal:** two years after the defense, then deleted; withdrawal at any time, with their record deleted.

Suggested wording:

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

- **Sittings and readings:** how many sittings, and whether each uses the same reading. The app does not need this settled; the classes do, before the dry run.
- **Qualitative analysis:** add or drop (analysis item 7).
- **Recruitment scope:** RVRCOB only, or all DLSU undergraduates with the business readings kept. The wider pool would help the small sample.
- **Sample size:** whether more than 45 can be recruited, given what 15 per group can detect.
