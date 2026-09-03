"""The Tutor Agent: build prompt -> call provider -> return what the student reads.

Everything the student sees comes from here. The agent is told which situation it
is writing for and never works it out itself, because pass/fail and step
advancement belong to the Orchestrator. See docs/context/agent-contracts.md.

Unlike the Assessment Agent there is nothing to parse: the model returns prose
and that prose is the output.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from collections.abc import Iterator

from .retry import complete_with_backoff, stream_with_backoff

# The four situations the Orchestrator can hand over. The agent writes for the
# one it is given; it never infers which applies.
FIRST_ATTEMPT = "first_attempt"
RETRY = "retry"
FINAL_FAIL = "final_fail"
PASSED = "passed"

SITUATIONS = (FIRST_ATTEMPT, RETRY, FINAL_FAIL, PASSED)

# What each situation asks for, in the agent's own terms. Kept here rather than
# in the prompt because it changes per turn.
_INSTRUCTION = {
    FIRST_ATTEMPT: (
        "This is the student's first attempt at this step. Write the question "
        "that opens it."
    ),
    RETRY: (
        "The response below did not pass, and the student has attempts left. "
        "Acknowledge the attempt, say what was missing, and ask again."
    ),
    FINAL_FAIL: (
        "The response below did not pass, and the student has no attempts left. "
        "Acknowledge the attempt and say what was missing. Do NOT ask again and "
        "do NOT suggest trying anything further: there is no attempt for the "
        "student to use."
    ),
    PASSED: (
        "The response below passed every criterion. Acknowledge it, saying what "
        "the student did well, and confirm the step is complete."
    ),
}


@dataclass
class TutorResult:
    text: str = ""
    error: str = ""
    usage: dict | None = None          # {input_tokens, output_tokens, ...}
    finish_reason: str | None = None   # why the model stopped, e.g. STOP

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.text.strip())

    def to_dict(self) -> dict:
        return asdict(self)


def _components(core_components) -> list[str]:
    """Core components arrive either as a list or, from the dataset, joined by '||'."""
    if not core_components:
        return []
    if isinstance(core_components, str):
        return [p.strip() for p in core_components.split("||") if p.strip()]
    return [str(p).strip() for p in core_components if str(p).strip()]


class TutorAgent:
    def __init__(self, provider, system_prompt: str):
        self.provider = provider
        self.system_prompt = system_prompt

    @staticmethod
    def build_user_prompt(reading, seei_step, situation, core_components=None,
                          user_response=None, unmet=None, attempts_left=None) -> str:
        """Assemble one turn.

        unmet: [(criterion, reason), ...] from the Assessment Agent's judgment.
        Supplied on RETRY and FINAL_FAIL, ignored otherwise.
        """
        if situation not in SITUATIONS:
            raise ValueError(f"Unknown situation: {situation!r}")

        parts = [f"# EXPOSITORY TEXT\n{reading}"]

        comps = _components(core_components)
        if comps:
            listed = "\n".join(f"- {c}" for c in comps)
            parts.append(
                "# CORE COMPONENTS\n"
                "The essential parts of the concept this text covers:\n"
                f"{listed}"
            )

        parts.append(f"# CURRENT SEE-I STEP\n{seei_step}")

        situation_line = _INSTRUCTION[situation]
        if situation == RETRY and attempts_left is not None:
            situation_line += (
                f" After this the student has {attempts_left} "
                f"{'attempt' if attempts_left == 1 else 'attempts'} left."
            )
        parts.append(f"# SITUATION\n{situation_line}")

        if situation != FIRST_ATTEMPT and user_response:
            parts.append(f"# THE STUDENT'S RESPONSE\n{user_response}")

        if situation in (RETRY, FINAL_FAIL) and unmet:
            lines = "\n".join(
                f"- {name}: {reason}" if reason else f"- {name}"
                for name, reason in unmet
            )
            parts.append(
                "# CRITERIA NOT MET\n"
                "Judged by the Assessment Agent. Work from these; do not re-judge "
                "the response or add criteria of your own.\n"
                f"{lines}"
            )

        parts.append(
            "Write the message the student will read. Prose only, no headings, "
            "no lists, no labels naming the dialogue moves."
        )
        return "\n\n".join(parts)

    def speak(self, reading, seei_step, situation, core_components=None,
              user_response=None, unmet=None, attempts_left=None,
              max_rate_limit_retries=3) -> TutorResult:
        prompt = self.build_user_prompt(
            reading, seei_step, situation,
            core_components=core_components,
            user_response=user_response,
            unmet=unmet,
            attempts_left=attempts_left,
        )
        raw, err = complete_with_backoff(
            self.provider, self.system_prompt, prompt, max_rate_limit_retries
        )
        if err is not None:
            return TutorResult(error=err)

        result = TutorResult(text=(raw or "").strip())
        result.usage = getattr(self.provider, "last_usage", None)
        result.finish_reason = getattr(self.provider, "last_finish_reason", None)
        if not result.text:
            result.error = "Tutor returned an empty message"
        return result

    def speak_stream(self, reading, seei_step, situation, core_components=None,
                     user_response=None, unmet=None, attempts_left=None,
                     max_rate_limit_retries=3) -> Iterator[str]:
        """Same as `speak`, but yields the message in pieces as it is generated.

        The caller accumulates the chunks into the full text to store. Token
        usage, if the provider reports it, is on `provider.last_usage` once the
        stream is exhausted. A provider failure raises rather than returning a
        TutorResult, because there is no single value to return from a generator;
        the caller streaming to a client turns that into an error event.
        """
        prompt = self.build_user_prompt(
            reading, seei_step, situation,
            core_components=core_components,
            user_response=user_response,
            unmet=unmet,
            attempts_left=attempts_left,
        )
        yield from stream_with_backoff(
            self.provider, self.system_prompt, prompt, max_rate_limit_retries
        )
