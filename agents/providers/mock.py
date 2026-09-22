"""Offline stub provider for smoke-testing the pipeline + report with no API key.

It does NOT assess anything. By default every response passes, which exercises
the CSV -> agent -> report wiring end to end (e.g. in CI or a first local run).
Real evaluation needs gemini or openai_compat.

**Making it fail on purpose.** A response containing `FAIL_MARKER` is judged to
miss the step's first two criteria. Without this the retry, fallback and
criterion-feedback paths cannot be seen at all without a paid provider, which
made the whole failure half of the app unreviewable offline.
"""

from __future__ import annotations

import json
import re

from .base import LLMProvider
from ..rubric import canonical_step, criteria_for

#: Put this anywhere in a response to make the mock fail it. Upper case and
#: unnatural on purpose: no real answer contains it by accident.
FAIL_MARKER = "XFAIL"


class MockProvider(LLMProvider):
    name = "mock"
    model_name = "mock"

    def __init__(self, config: dict):
        self.config = config
        self.last_usage = None
        self.last_finish_reason = None

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        # Fake usage so the cost-logging path can be smoke-tested offline.
        self.last_usage = {
            "input_tokens": 1500,
            "output_tokens": 200,
            "thinking_tokens": 0,
            "total_tokens": 1700,
        }
        self.last_finish_reason = "STOP"

        # A tutor prompt carries a SITUATION section; an assessment prompt does
        # not. The tutor wants prose, so returning the assessment JSON here would
        # be wrong. This only affects tutor prompts, which the eval never sends,
        # so the eval's mock smoke test is unchanged.
        if "# SITUATION" in user_prompt:
            return self._tutor_prose(user_prompt)

        # Emit a judgment for every criterion of the step named in the user
        # prompt, so the derive-verdict path is exercised end to end offline.
        # Everything passes unless the response asks to fail.
        m = re.search(r"#\s*CURRENT SEE-I STEP\s*\n\s*(.+)", user_prompt)
        step = canonical_step(m.group(1).strip()) if m else None
        names = criteria_for(step) if step else []

        response = self._section(user_prompt, "# STUDENT RESPONSE")
        failing = names[:2] if FAIL_MARKER in response.upper() else []

        criteria = {
            c: {
                "pass": c not in failing,
                "reason": (
                    f"[MOCK] {FAIL_MARKER} was in the response"
                    if c in failing
                    else "[MOCK] always passes"
                ),
            }
            for c in names
        }
        return json.dumps(
            {
                "verdict": "FAIL" if failing else "PASS",
                "fail_criteria": failing,
                "criteria": criteria,
                "raw_response": "[MOCK] no real assessment performed",
            }
        )

    @staticmethod
    def _section(prompt: str, heading: str) -> str:
        """The text under a `# HEADING`, up to the next heading or the end."""
        m = re.search(rf"{re.escape(heading)}\s*\n(.*?)(?=\n#\s|\Z)", prompt, re.S)
        return m.group(1) if m else ""

    @staticmethod
    def _tutor_prose(user_prompt: str) -> str:
        m = re.search(r"#\s*CURRENT SEE-I STEP\s*\n\s*(.+)", user_prompt)
        step = m.group(1).strip() if m else "this step"
        s = re.search(r"#\s*SITUATION\s*\n\s*(.+)", user_prompt)
        situation = s.group(1).strip() if s else ""
        return f"[MOCK tutor] {step}. {situation[:80]}"

    def complete_with_file(
        self, system_prompt: str, user_prompt: str, data: bytes, mime_type: str
    ) -> str:
        """Pretend to describe a document's figures, without looking at it.

        It cannot see the document, so it reads the captions out of the
        extracted text the prompt carries: every line that starts "Figure 2" or
        "Table 6.1" gets a placeholder description. That is enough to exercise
        placing descriptions in the text, offline and for free.
        """
        self.last_usage = {
            "input_tokens": 2500, "output_tokens": 150,
            "thinking_tokens": 0, "total_tokens": 2650,
        }
        self.last_finish_reason = "STOP"
        text = self._section(user_prompt, "# EXTRACTED TEXT")
        figures, seen = [], set()
        for m in re.finditer(
            r"^((?:Figure|Fig\.|Table)\s+\d+(?:\.\d+)*).*$", text, re.M
        ):
            # The first line naming a figure is its caption; later ones are
            # prose that mentions it ("Figure 6.4 shows...").
            if m.group(1) in seen:
                continue
            seen.add(m.group(1))
            figures.append({
                "page": None,
                "label": m.group(1),
                "caption": m.group(0).strip(),
                "description": f"[MOCK] A description of {m.group(1)} would appear here.",
            })
        return json.dumps({"figures": figures})

    def stream(self, system_prompt: str, user_prompt: str):
        """Yield the mock answer in word-sized pieces, so streaming is exercised.

        Usage and finish reason are set the same way `complete()` sets them, so a
        streamed tutor turn still records its (fake) token counts offline.
        """
        text = self.complete(system_prompt, user_prompt)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word if i == 0 else " " + word
