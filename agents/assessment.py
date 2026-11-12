"""The Student Assessment Agent under test: build prompt -> call provider -> parse.

Parsing is defensive: it tolerates code fences, normalizes criterion names, and
records warnings (e.g. hallucinated criteria, verdict/criteria mismatch) without
crashing — those warnings are themselves useful signals during prompt iteration.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from .retry import complete_with_backoff
from .rubric import canonical_criterion, canonical_step, criteria_for


@dataclass
class CriterionJudgment:
    passed: bool
    reason: str = ""


@dataclass
class AgentResult:
    verdict: str | None = None                       # "PASS" | "FAIL" | None (DERIVED in code)
    model_verdict: str | None = None                 # what the model stated (cross-check only)
    fail_criteria: list[str] = field(default_factory=list)
    criteria: dict[str, CriterionJudgment] = field(default_factory=dict)
    raw_text: str = ""
    parse_ok: bool = True
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    usage: dict | None = None   # {input_tokens, output_tokens, thinking_tokens, total_tokens}
    finish_reason: str | None = None   # why the model stopped, e.g. STOP / MAX_TOKENS

    def to_dict(self) -> dict:
        d = asdict(self)
        d["criteria"] = {k: asdict(v) for k, v in self.criteria.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AgentResult":
        crit = {k: CriterionJudgment(**v) for k, v in (d.get("criteria") or {}).items()}
        return cls(
            verdict=d.get("verdict"),
            model_verdict=d.get("model_verdict"),
            fail_criteria=list(d.get("fail_criteria") or []),
            criteria=crit,
            raw_text=d.get("raw_text", ""),
            parse_ok=d.get("parse_ok", True),
            error=d.get("error", ""),
            warnings=list(d.get("warnings") or []),
            usage=d.get("usage"),
            finish_reason=d.get("finish_reason"),
        )


def _extract_json(text: str) -> str:
    """Pull the first JSON object out of a model response (handles ``` fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    return brace.group(0) if brace else text


def parse_result(raw_text: str, step: str) -> AgentResult:
    """Parse + validate the model's JSON for a given SEE-I step."""
    result = AgentResult(raw_text=raw_text)

    canon_step = canonical_step(step)
    if canon_step is None:
        result.parse_ok = False
        result.error = f"Unknown SEE-I step: {step!r}"
        return result
    valid_names = criteria_for(canon_step)

    try:
        data = json.loads(_extract_json(raw_text))
    except (json.JSONDecodeError, ValueError) as e:
        result.parse_ok = False
        result.error = f"JSON parse failed: {e}"
        return result
    if not isinstance(data, dict):
        result.parse_ok = False
        result.error = "Top-level JSON is not an object"
        return result

    # the model's stated verdict — kept ONLY as a self-consistency cross-check.
    # The authoritative verdict is derived in code from the per-criterion judgments.
    model_verdict = str(data.get("verdict", "")).strip().upper()
    if model_verdict not in ("PASS", "FAIL"):
        if data.get("verdict") is not None:
            result.warnings.append(f"Invalid model verdict: {data.get('verdict')!r}")
        model_verdict = None
    result.model_verdict = model_verdict

    # per-criterion judgments (required — we derive the verdict from these)
    raw_criteria = data.get("criteria") or {}
    if isinstance(raw_criteria, dict):
        for name, val in raw_criteria.items():
            canon = canonical_criterion(canon_step, str(name))
            if canon is None:
                result.warnings.append(f"Unknown criterion in 'criteria': {name!r}")
                continue
            if isinstance(val, dict):
                passed = bool(val.get("pass", val.get("passed", True)))
                reason = str(val.get("reason", ""))
            else:
                passed = bool(val)
                reason = ""
            result.criteria[canon] = CriterionJudgment(passed=passed, reason=reason)

    # DERIVE the authoritative verdict + fail list from the per-criterion judgments
    # (the rubric rule: any failing criterion => FAIL; all passing => PASS).
    if result.criteria:
        missing = [c for c in valid_names if c not in result.criteria]
        if missing:
            result.warnings.append(f"Model did not judge every criterion; missing {missing}")
        result.fail_criteria = [c for c in valid_names
                                if c in result.criteria and not result.criteria[c].passed]
        result.verdict = "FAIL" if result.fail_criteria else "PASS"
    else:
        # no per-criterion object to derive from — fall back to the model's own list
        result.warnings.append("No 'criteria' object returned; falling back to model verdict")
        raw_fail = data.get("fail_criteria")
        fails: list[str] = []
        if isinstance(raw_fail, list):
            for name in raw_fail:
                canon = canonical_criterion(canon_step, str(name))
                if canon and canon not in fails:
                    fails.append(canon)
        result.fail_criteria = fails
        result.verdict = model_verdict if model_verdict else ("FAIL" if fails else None)

    # cross-check: warn when the model's own statements disagree with what we derived
    if model_verdict and result.verdict and model_verdict != result.verdict:
        result.warnings.append(
            f"model stated verdict={model_verdict} but criteria imply {result.verdict}"
        )
    raw_fail = data.get("fail_criteria")
    if isinstance(raw_fail, list) and result.criteria:
        model_fails = {canonical_criterion(canon_step, str(n)) for n in raw_fail}
        model_fails.discard(None)
        if model_fails != set(result.fail_criteria):
            result.warnings.append(
                f"model fail_criteria {sorted(model_fails)} != derived {sorted(result.fail_criteria)}"
            )

    return result


class AssessmentAgent:
    def __init__(self, provider, system_prompt: str):
        self.provider = provider
        self.system_prompt = system_prompt

    @staticmethod
    def build_user_prompt(reading, seei_step, user_response, key_concept=None) -> str:
        kc = ""
        if key_concept:
            # a reading may have several core components in one cell, separated by "||"
            parts = [p.strip() for p in str(key_concept).split("||") if p.strip()]
            items = "\n".join(f"- {p}" for p in parts)
            kc = ("# KEY CONCEPT (authoritative reference)\n"
                  "The reading's core component(s) of the concept — use these when judging "
                  "Accuracy (the response must be faithful to them) and Completeness (State must "
                  "name them; Elaborate must explain them):\n"
                  f"{items}\n\n")
        return (
            f"# READING\n{reading}\n\n"
            f"{kc}"
            f"# CURRENT SEE-I STEP\n{seei_step}\n\n"
            f"# STUDENT RESPONSE\n{user_response}\n\n"
            "Assess the STUDENT RESPONSE against the rubric criteria for the CURRENT "
            "SEE-I STEP only, and return the JSON object specified in your instructions."
        )

    def assess(self, reading, seei_step, user_response,
               retries=1, max_rate_limit_retries=3, key_concept=None) -> AgentResult:
        prompt = self.build_user_prompt(reading, seei_step, user_response, key_concept)
        last: AgentResult | None = None
        for _ in range(retries + 1):
            raw, err = self._complete(prompt, max_rate_limit_retries)
            if err is not None:
                # _complete already backed off internally; don't loop and pile on
                # more calls (that re-saturates a tight per-minute quota).
                return AgentResult(parse_ok=False, error=err)
            result = parse_result(raw, seei_step)
            result.usage = getattr(self.provider, "last_usage", None)
            result.finish_reason = getattr(self.provider, "last_finish_reason", None)
            if str(result.finish_reason).upper() in ("MAX_TOKENS", "LENGTH"):
                result.warnings.append(
                    f"finish_reason={result.finish_reason}: output truncated at "
                    "max_output_tokens — raise it"
                )
            if result.parse_ok and result.verdict in ("PASS", "FAIL"):
                return result
            last = result
        return last if last is not None else AgentResult(parse_ok=False, error="No response")

    def _complete(self, prompt: str, max_rate_limit_retries: int):
        return complete_with_backoff(self.provider, self.system_prompt, prompt,
                                     max_rate_limit_retries)
