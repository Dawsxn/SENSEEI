# Agent contracts

What each agent receives, what it returns, and who calls it.

Two agents call an LLM: the Tutor Agent and the Assessment Agent. The
Orchestrator drives both and calls no LLM itself.

## Division of labour

| Component | Calls an LLM | Owns |
| --- | --- | --- |
| Tutor Agent | Yes | Everything the student reads |
| Assessment Agent | Yes | Grading one response against the rubric |
| Orchestrator | No | Pass/fail, retries, step advancement, session state |

The Orchestrator is fixed-rule code. Any decision that must be deterministic,
reproducible, or auditable belongs to it and not to a prompt. If a rule starts
migrating into an agent's instructions, that is a mistake.

## Assessment Agent

Already implemented in `agents/assessment.py`. The eval harness in
`assessment-agent-eval/` measures this exact code, so a backend change here
changes what the eval validates. Do not fork it.

**Inputs** (Table 4.7):

| Input | Notes |
| --- | --- |
| Reading | Full text |
| Core components | The reading's essential defining parts. Several are joined with `\|\|` in one field |
| Current SEE-I step | State, Elaborate, Exemplify, or Illustrate |
| Student response | The single attempt being graded |

It does not receive prior attempts, the conversation, or the student's identity.
Each attempt is graded on its own.

**Output.** The model returns JSON:

```json
{
  "verdict": "FAIL",
  "fail_criteria": ["Clarity", "Accuracy"],
  "criteria": {
    "Clarity": { "pass": false, "reason": "starts with 'It' without naming the concept" },
    "Accuracy": { "pass": false, "reason": "contradicts the reading on X" }
  },
  "raw_response": "one-sentence justification"
}
```

**The verdict is derived in code, not taken from the model.** Any criterion with
`pass: false` means FAIL, all passing means PASS. The model's own `verdict` field
is recorded only to detect self-contradiction, and a mismatch raises a warning
rather than an error.

Parsing is deliberately tolerant: it strips code fences, normalises criterion
names against the rubric, and records warnings for hallucinated or missing
criteria instead of crashing. Warnings are signal, not noise, and should be
persisted rather than discarded.

The agent judges every criterion for the step and collects all failures. It never
stops at the first one.

## Tutor Agent

Implemented in `agents/tutor.py`. Returns prose, so there is nothing to parse.

**Inputs:**

| Input | When |
| --- | --- |
| Reading | Always |
| Core components | Always |
| Current SEE-I step | Always |
| The student's response text | Whenever a response has been graded |
| Failed criteria and their reasons from that response | When it did not pass |

**Output.** Plain text, the message the student reads. No JSON, no markup.

The Orchestrator names the **situation** and the agent writes for it. Since the
Orchestrator chose the situation, it already knows which dialogue moves the
message is composed of and records them itself. The agent is never asked which
moves it used.

| Situation | Moves | Output |
| --- | --- | --- |
| `FIRST_ATTEMPT` | Prompt | The question that opens the step |
| `RETRY` | Acknowledgement + Criterion-Based Feedback + Re-Prompt | What was missed, then ask again |
| `FINAL_FAIL` | Acknowledgement + Criterion-Based Feedback | What was missed, and nothing more |
| `PASSED` | Acknowledgement + Transition | What was done well, step complete |

`FINAL_FAIL` is not a new dialogue move. It is `RETRY` with `Re-Prompt` dropped,
because there is no attempt left to invite.

**Constraints:**

1. It never supplies the answer. Feedback names what was missed and redirects.
   The student revises their own response.
2. It receives the Assessment Agent's reasons and works from them. It does not
   re-derive what was wrong, and it does not second-guess the verdict.
3. It does not decide whether to advance, retry, or end the session. It is told
   which situation it is in and writes for that situation.
4. Feedback must speak to what the student actually wrote, not just name the
   criterion. See the feedback style section of the tutoring loop doc for the
   required three-part shape. This is why the response text is an input.

## Sequence

One step, from question to outcome (Figure 4.8):

```
1. Orchestrator asks the Tutor Agent for a Prompt
2. Student submits a response
3. Orchestrator sends reading, core components, step, response
   to the Assessment Agent
4. Assessment Agent returns per-criterion judgments
5. Orchestrator derives the verdict

   PASS  -> more steps left?
              yes: advance, back to 1 for the next step
              no:  session complete

   FAIL  -> attempts used up for this step?
              no:  ask the Tutor Agent for Acknowledgement +
                   Criterion-Based Feedback + Re-Prompt, passing
                   the response text, failed criteria, and reasons.
                   Back to 2.
              yes: fallback, session ends, instructor flagged
```

The Orchestrator holds the loop. Neither agent knows what happens after it
returns.

## Choosing the model and provider

`agents/providers/` holds one class per LLM backend: Gemini, any
OpenAI-compatible endpoint, and a mock for offline testing. `get_provider()`
takes a dict of settings and returns the matching class, so switching backends is
a settings change rather than a code change.

Something has to supply that dict. The eval builds it from
`assessment-agent-eval/config.yaml`:

```yaml
provider: gemini
model: gemini-3.1-pro-preview
api_key_env: GEMINI_API_KEY
temperature: 0
```

The backend will need answers to the same questions when it starts up, from its
own source rather than that file. The eval's copy is pinned for reproducible eval
runs, and pointing the app at it would tie the two together. Where the backend's
settings come from is open question 1.

One rule regardless: **the model the eval measures should be the model the app
runs.** If the eval grades with one model and students get another, the measured
alignment describes software nobody used.

## Decided

1. **The Tutor Agent's output is not formally evaluated.** Only the Assessment
   Agent has a harness. Revisit if Tutor behaviour becomes a research claim.
2. **The Tutor Agent receives the student's response text on a retry**, because
   feedback has to describe what the student actually wrote.
3. **The Tutor Agent's prompt is versioned and pinned per session**, the same way
   the Assessment Agent's is. This is for traceability, not evaluation: if the
   prompt changes partway through data collection, sessions before and after are
   not the same experience, and without a stamp there is no way to tell them
   apart afterwards.
4. **A provider failure never consumes an attempt.** When a call fails after
   retries are exhausted, show the student an error, leave the session at the
   same step with the same attempt count, and let them resubmit. A student losing
   one of three attempts to a network timeout would be invisible in the data and
   would quietly corrupt the per-step attempt statistics.
5. **The fallback message is not written by the Tutor.** When attempts run out
   the agent writes the feedback, and the "contact your instructor" message that
   follows is static copy. It is the same sentence every time, and generating it
   invites the model to soften it or add a hint the student cannot act on.
6. **Both agents share `agents/retry.py`** for rate-limit backoff, so the two
   cannot drift in how they handle a 429.
7. **`json_mode` separates them at the provider.** The Assessment Agent needs
   JSON output; the Tutor Agent needs prose. Gemini forced JSON unconditionally
   until this was made configurable, defaulting to on.

## Open questions

| # | Question | Blocks |
| --- | --- | --- |
| 1 | Where does the backend read its provider, model, and API key from at startup? Environment variables are the usual answer, read once into a settings object. Really a tech-stack decision, and can move to that doc when it exists. | Backend bootstrap |

## Related

- `docs/context/student-tutoring-loop.md`, the loop these contracts serve
- `docs/context/data-model.md`, how judgments persist
- `agents/assessment.py`, the implementation
- `assessment-agent-eval/CONTEXT.md`, how the Assessment Agent is measured
