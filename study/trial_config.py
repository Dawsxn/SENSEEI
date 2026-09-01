"""The pinned settings for one trial run, loaded from ``study/trial.yaml``.

Everything that must be identical for all 45 participants lives in one file: the
model, the reading, the timing, and the allocation seed. Three reasons it is a
file rather than scattered defaults.

**The reading has to be swappable.** Which expository text the trial uses is not
settled, and Section 4.6.3 requires participants who have not previously studied
its concept — which may well decide the choice. Changing it is one line here.

**The model has to be pinned and provable.** Section 4.6.2 requires the unguided
arm to run "the same underlying model as SENSEE-I's agents", so that the variable
separating the two AI-assisted arms is the SEE-I scaffolding rather than model
capability. A model string typed into two places will eventually disagree, and
the disagreement would invalidate the comparison without anything failing. So it
is written once here, and :func:`assert_model_parity` checks the claim against
what the Assessment Agent actually resolves to rather than trusting it.

**The run has to be reproducible.** The allocation seed, the reading checksum,
and the model are stamped onto the exported data, so any reported result can be
traced back to the exact inputs that produced it — the same discipline the eval
harness already applies to its runs.

A note on where the model comes from. The SENSEE-I application has no settings
source yet: "where does the backend read its provider, model, and API key from at
startup?" is still open in ``docs/context/agent-contracts.md``. Until it exists,
this file is the pin, and it deliberately mirrors the eval harness's
``config.yaml``, which is the only other place a model is currently fixed. When
the app gains its own configuration, :func:`assert_model_parity` is the thing to
point at it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .phases import TrialTiming
from .randomisation import DEFAULT_BLOCK_SIZE, Allocation, generate_allocation

#: Providers that cannot produce real data. Allowed only in a dry run.
SYNTHETIC_PROVIDERS = frozenset({"mock"})


class TrialConfigError(ValueError):
    """The configuration cannot produce a valid trial."""


@dataclass(frozen=True)
class ReadingConfig:
    """The single expository text every arm receives (§4.6.2)."""

    path: Path
    title: str
    core_components: tuple[str, ...] = ()

    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def checksum(self) -> str:
        """SHA-256 of the text, for the pre-flight identity check.

        The harness serves this text to the passive and unguided arms; the
        SENSEE-I arm receives it through the application's own reading upload.
        Those are two copies of one document, and if they ever diverge the arms
        are no longer reading the same thing — a difference that would quietly
        confound every comparison. Comparing checksums before the run is the
        cheapest way to know they have not.
        """
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class LLMConfig:
    """Which model the unguided arm runs, and how hard it may be pushed.

    Shaped to be passed straight to ``agents.providers.get_provider``, so the
    unguided arm reaches the model through exactly the code SENSEE-I's agents
    use. That is what makes the parity requirement of §4.6.2 structural rather
    than a promise.
    """

    provider: str = "gemini"
    model: str = "gemini-3.1-pro-preview"
    api_key_env: str = "GEMINI_API_KEY"
    base_url: str | None = None

    #: Left at the provider default rather than pinned to 0. The unguided arm is
    #: meant to be an ordinary chat experience (§4.6.2: "no constraint on how the
    #: tool is used"), and the eval's temperature 0 exists for reproducible
    #: grading, which is a different job.
    temperature: float | None = None

    #: Ceiling on a single reply, not a cost.
    max_output_tokens: int = 4096

    #: Throttle, shared across all concurrent participants. See the capacity note
    #: in trial.yaml: a single sitting puts every AI-arm participant on the
    #: provider at once, which is a far heavier load than the eval ever placed.
    requests_per_minute: int = 60

    def provider_settings(self) -> dict:
        """The dict ``get_provider`` expects. Prose output, so JSON mode is off."""
        settings: dict = {
            "provider": self.provider,
            "model": self.model,
            "api_key_env": self.api_key_env,
            "max_output_tokens": self.max_output_tokens,
            "json_mode": False,
        }
        if self.base_url:
            settings["base_url"] = self.base_url
        if self.temperature is not None:
            settings["temperature"] = self.temperature
        return settings

    @property
    def fingerprint(self) -> str:
        """What must match between the unguided arm and SENSEE-I's agents."""
        return f"{self.provider}:{self.model}"

    @property
    def is_synthetic(self) -> bool:
        return self.provider.strip().lower() in SYNTHETIC_PROVIDERS


@dataclass(frozen=True)
class TrialConfig:
    """Everything pinned for one trial run."""

    trial_id: str
    reading: ReadingConfig
    llm: LLMConfig = field(default_factory=LLMConfig)

    participants: int = 45
    block_size: int = DEFAULT_BLOCK_SIZE
    allocation_seed: int = 0

    intervention_minutes: int = 40

    #: All participants run at the same time in one lab session. Recorded because
    #: it drives capacity: every AI-arm participant is on the provider at once.
    one_sitting: bool = True

    #: Where the SENSEE-I application lives, for the arm that uses it.
    senseei_base_url: str = ""

    #: A rehearsal rather than real collection. Relaxes the checks that would
    #: otherwise refuse a synthetic model or a fake link.
    dry_run: bool = False

    @property
    def timing(self) -> TrialTiming:
        return TrialTiming(intervention_seconds=self.intervention_minutes * 60)

    def allocation(self) -> Allocation:
        """The assignment sequence for this trial. Deterministic given the seed."""
        return generate_allocation(
            self.participants,
            seed=self.allocation_seed,
            block_size=self.block_size,
        )

    @property
    def concurrent_ai_participants(self) -> int:
        """How many participants may hit the LLM at once.

        Two of the three arms use a model, so a single sitting puts two thirds of
        the cohort on the provider simultaneously for forty minutes.
        """
        if not self.one_sitting:
            return 0
        return (self.participants * 2) // 3

    def validate(self) -> None:
        """Refuse a configuration that cannot produce usable data.

        Called before a run starts. Every check here is something that would
        otherwise be discovered during analysis, when it is far too late.
        """
        problems: list[str] = []

        if not self.trial_id.strip():
            problems.append("trial_id is empty; the export has nothing to key on.")

        if not self.reading.path.exists():
            problems.append(f"Reading not found at {self.reading.path}.")
        elif not self.reading.path.read_text(encoding="utf-8").strip():
            problems.append(f"Reading at {self.reading.path} is empty.")

        try:
            self.allocation()
        except ValueError as exc:
            problems.append(str(exc))

        if self.intervention_minutes <= 0:
            problems.append(
                f"Intervention must last a positive time, got {self.intervention_minutes}m."
            )

        if not self.dry_run:
            if self.llm.is_synthetic:
                problems.append(
                    f"Provider {self.llm.provider!r} cannot produce real responses. "
                    "Set dry_run: true, or pin a real provider."
                )
            if self.allocation_seed == 0:
                problems.append(
                    "allocation_seed is unset. Set it deliberately and record it, "
                    "so the assignment can be re-derived and audited afterwards."
                )
            if not self.senseei_base_url.strip():
                problems.append(
                    "senseei_base_url is unset; the SENSEE-I arm has nowhere to go."
                )

        if problems:
            raise TrialConfigError(
                "Trial configuration is not runnable:\n  - " + "\n  - ".join(problems)
            )

    def stamp(self) -> dict:
        """Provenance recorded alongside the data this run produces."""
        return {
            "trial_id": self.trial_id,
            "provider": self.llm.provider,
            "model": self.llm.model,
            "reading_title": self.reading.title,
            "reading_checksum": self.reading.checksum(),
            "allocation_seed": self.allocation_seed,
            "block_size": self.block_size,
            "participants": self.participants,
            "intervention_minutes": self.intervention_minutes,
            "one_sitting": self.one_sitting,
            "dry_run": self.dry_run,
        }


def load_trial_config(path: str | Path | None = None) -> TrialConfig:
    """Read ``trial.yaml``. Paths inside it resolve relative to the file itself."""
    import yaml

    path = Path(path) if path else Path(__file__).parent / "trial.yaml"
    if not path.exists():
        raise TrialConfigError(f"No trial configuration at {path}.")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    root = path.parent

    reading_raw = data.get("reading") or {}
    if not reading_raw.get("path"):
        raise TrialConfigError(f"{path} does not name a reading path.")

    reading_path = Path(reading_raw["path"])
    if not reading_path.is_absolute():
        reading_path = root / reading_path

    reading = ReadingConfig(
        path=reading_path,
        title=str(reading_raw.get("title", "")),
        core_components=tuple(reading_raw.get("core_components") or ()),
    )

    llm_raw = data.get("llm") or {}
    known = LLMConfig.__dataclass_fields__.keys()
    llm = LLMConfig(**{k: v for k, v in llm_raw.items() if k in known and v is not None})

    return TrialConfig(
        trial_id=str(data.get("trial_id", "")),
        reading=reading,
        llm=llm,
        participants=int(data.get("participants", 45)),
        block_size=int(data.get("block_size", DEFAULT_BLOCK_SIZE)),
        allocation_seed=int(data.get("allocation_seed", 0)),
        intervention_minutes=int(data.get("intervention_minutes", 40)),
        one_sitting=bool(data.get("one_sitting", True)),
        senseei_base_url=str(data.get("senseei_base_url", "")),
        dry_run=bool(data.get("dry_run", False)),
    )


def assert_model_parity(config: TrialConfig, senseei_fingerprint: str | None) -> None:
    """Check the unguided arm and SENSEE-I's agents are on the same model (§4.6.2).

    ``senseei_fingerprint`` is ``"<provider>:<model>"`` as the application
    actually resolves it. Pass None while the application has no settings source
    to read — that is the current state, and it is a gap to close before the
    trial, not a reason to skip the check afterwards.

    A mismatch is fatal. If the two arms run different models, the study's
    comparison measures model capability as well as SEE-I scaffolding, and no
    amount of care in the analysis can separate them again.
    """
    if senseei_fingerprint is None:
        raise TrialConfigError(
            "Cannot verify model parity: the SENSEE-I application does not report "
            "which model it runs. Section 4.6.2 requires both AI arms to share one "
            f"model, and this trial pins {config.llm.fingerprint!r}. Confirm the "
            "application resolves to the same, then wire it into this check."
        )

    if senseei_fingerprint != config.llm.fingerprint:
        raise TrialConfigError(
            "Model parity is broken: the unguided arm runs "
            f"{config.llm.fingerprint!r} but SENSEE-I runs {senseei_fingerprint!r}. "
            "Section 4.6.2 requires one model across both AI arms, so that the "
            "variable under test is the SEE-I scaffolding and not the model."
        )
