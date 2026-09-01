"""Turning a finished trial into files the analysis of Section 4.6.5 can read.

Two bundles, and they must not be one.

**The analysis bundle** carries everything: per-item answers, the engagement
measures of Section 4.6.3, per-phase durations, transcripts, and the SBA
responses with their arm attached. It is what the ANOVAs, the SUS composite, and
the exclusion decisions are computed from.

**The rater bundle** carries almost nothing: SBA response text under a blind key,
in an order shuffled per rater, with empty score columns. Section 4.6.5 requires
the two faculty to grade "independently and blindly", and a file where the arm is
visible — or where all the SENSEE-I responses happen to sit together — is not
blind. This is the single place where withholding information is the point, so
it gets its own function rather than a flag on the other one.

**Nothing carries a name.** Section 4.6.6 keys performance records to the
participant identifier rather than to identity, and the export is where that
promise is kept: the identity table is never read. There is a test asserting no
exported file contains a participant's name.

Long-form rather than wide for anything item-level. Instruments differ in how
many items they have, and a wide table would be mostly empty columns that break
the moment an item is added.

Usage::

    python -m study.export                 # analysis bundle into export/
    python -m study.export --raters A,B    # plus a blind bundle per rater
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .arms import Arm
from .exclusion import build_engagement_record
from .grading import DIMENSIONS, build_blind_set, order_for
from .phases import Phase, phase_durations, ran_out_of_time, utcnow


@dataclass(frozen=True)
class ExportResult:
    """What an export wrote, for the console and for the log."""

    directory: Path
    files: tuple[str, ...]
    participants: int
    sba_responses: int


def export_analysis(
    store,
    directory: str | Path = "export",
    link=None,
    now: datetime | None = None,
) -> ExportResult:
    """Write the analysis bundle.

    Everything is keyed to ``participant_id``. The identity table is not read,
    so a name cannot reach these files even by accident.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    now = now or utcnow()

    participants = sorted(store.all(), key=lambda p: p.participant_id)
    written: list[str] = []

    written.append(_write(directory, "participants.csv",
                          _participant_rows(participants, now, link)))
    written.append(_write(directory, "instrument_scores.csv",
                          _instrument_score_rows(participants)))
    written.append(_write(directory, "instrument_answers.csv",
                          _answer_rows(participants)))
    written.append(_write(directory, "phase_durations.csv",
                          _phase_duration_rows(participants)))
    written.append(_write(directory, "unguided_transcripts.csv",
                          _transcript_rows(participants)))
    written.append(_write(directory, "passive_reading.csv",
                          _passive_rows(participants)))
    written.append(_write(directory, "senseei_sessions.csv",
                          _senseei_rows(participants, link)))

    sba = _sba_responses(participants)
    written.append(_write(directory, "sba_responses.csv",
                          [{"participant_id": pid, "arm": arm, "response": text}
                           for pid, arm, text in sba]))

    manifest = _manifest(store, participants, now)
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    written.append("manifest.json")

    return ExportResult(
        directory=directory,
        files=tuple(f for f in written if f),
        participants=len(participants),
        sba_responses=len(sba),
    )


def export_for_raters(
    store,
    raters: tuple[str, ...],
    directory: str | Path = "export",
    subset: int | None = None,
    seed: int = 0,
) -> ExportResult:
    """Write one blind grading file per rater, plus the key that maps back.

    The key is written to ``rater_key.csv`` and is for the research team only —
    it is what lets the graded scores be rejoined to participants afterwards, and
    handing it to a rater would undo the blinding entirely.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    responses = {
        participant_id: text
        for participant_id, _, text in _sba_responses(sorted(
            store.all(), key=lambda p: p.participant_id
        ))
    }
    salt = getattr(store.config, "trial_id", "") or "trial"
    blind, key = build_blind_set(responses, salt, raters, subset=subset, seed=seed)

    written: list[str] = []
    for rater in raters:
        rows = [
            {
                "response_id": response.response_id,
                "response": response.text,
                **{dimension: "" for dimension in DIMENSIONS},
                "note": "",
            }
            for response in order_for(blind, rater, seed=seed)
        ]
        written.append(_write(directory, f"rater_{_slug(rater)}.csv", rows))

    written.append(_write(
        directory,
        "rater_key.csv",
        [{"response_id": r, "participant_id": p} for r, p in sorted(key.items())],
    ))

    return ExportResult(
        directory=directory,
        files=tuple(f for f in written if f),
        participants=len(responses),
        sba_responses=len(blind),
    )


# --- the rows -------------------------------------------------------------


def _participant_rows(participants, now, link) -> list[dict]:
    rows = []
    for participant in participants:
        record = build_engagement_record(participant, now, link)
        row = {
            "participant_id": participant.participant_id,
            "arm": participant.arm.value,
            "checked_in_at": _iso(participant.checked_in_at),
            "phase_reached": participant.state.phase.value,
            "completed": participant.state.phase is Phase.DONE,
            "ran_out_of_time": ran_out_of_time(participant.state),
            "attention_failed": record.attention_failed,
            "attention_answered": record.attention_answered,
            "tool_failed": bool(record.unavailable),
            "incidents": len(participant.incidents),
            "sus_score": participant.sus_score,
        }
        # The §4.6.3 measures, named by arm. Absent for the other arms rather
        # than zero: a passive participant has no turn count, and writing 0
        # would put them below any threshold set on it.
        row.update({m.key: m.value for m in record.measures})
        rows.append(row)
    return rows


def _instrument_score_rows(participants) -> list[dict]:
    return [
        {
            "participant_id": participant.participant_id,
            "arm": participant.arm.value,
            "phase": phase.value,
            "instrument": result.instrument_id,
            "correct": result.correct,
            "scored": result.scored,
            "attention_failed": result.attention_failed,
            "attention_answered": result.attention_answered,
            "complete": result.is_complete,
            "sus_score": result.sus_score,
        }
        for participant in participants
        for phase, result in sorted(
            participant.responses.items(), key=lambda kv: kv[0].value
        )
    ]


def _answer_rows(participants) -> list[dict]:
    """Item-level answers, long form.

    One row per answer rather than one column per item: instruments differ in
    length, and a wide table would break the moment an item is added.
    """
    return [
        {
            "participant_id": participant.participant_id,
            "arm": participant.arm.value,
            "instrument": result.instrument_id,
            "item_id": item_id,
            "answer": answer,
        }
        for participant in participants
        for result in participant.responses.values()
        for item_id, answer in sorted(result.answers.items())
    ]


def _phase_duration_rows(participants) -> list[dict]:
    """How long each phase took.

    Not bookkeeping. Time-on-task varies between participants now that the
    period is a ceiling rather than a floor, so these are what the analysis uses
    to account for it.
    """
    return [
        {
            "participant_id": participant.participant_id,
            "arm": participant.arm.value,
            "phase": phase.value,
            "seconds": round(duration.total_seconds(), 1),
        }
        for participant in participants
        for phase, duration in sorted(
            phase_durations(participant.state).items(), key=lambda kv: kv[0].value
        )
    ]


def _transcript_rows(participants) -> list[dict]:
    """The unguided arm's conversations, one row per turn.

    The only record of what unguided use actually looked like for these
    participants, which is the behaviour §2.1 characterises and the arm exists
    to represent.
    """
    rows = []
    for participant in participants:
        if participant.unguided is None:
            continue
        for index, turn in enumerate(participant.unguided.conversation.turns, start=1):
            rows.append({
                "participant_id": participant.participant_id,
                "turn": index,
                "speaker": turn.speaker.value,
                "at": _iso(turn.at),
                "words": turn.word_count,
                "failed": turn.failed,
                "text": turn.text,
            })
    return rows


def _passive_rows(participants) -> list[dict]:
    rows = []
    for participant in participants:
        if participant.passive is None:
            continue
        telemetry = participant.passive.telemetry()
        rows.append({
            "participant_id": participant.participant_id,
            "time_on_text_seconds": round(telemetry.time_on_text.total_seconds(), 1),
            "max_scroll_depth": round(telemetry.max_scroll_depth, 3),
            "away_count": telemetry.away_count,
            "scroll_samples": telemetry.sample_count,
        })
    return rows


def _senseei_rows(participants, link) -> list[dict]:
    """What the SENSEE-I arm's sessions did, read back through the link.

    Carries the rubric, prompt and model versions, so a session stays
    interpretable if any of them changed during collection.
    """
    if link is None:
        return []

    rows = []
    for participant in participants:
        if participant.arm is not Arm.SENSEEI:
            continue
        telemetry = link.fetch_telemetry(participant.participant_id)
        if telemetry is None:
            continue
        rows.append({
            "participant_id": participant.participant_id,
            "session_id": telemetry.session_id,
            "status": telemetry.status,
            "started_at": _iso(telemetry.started_at),
            "ended_at": _iso(telemetry.ended_at),
            "duration_seconds": (
                round(telemetry.duration.total_seconds(), 1)
                if telemetry.duration else None
            ),
            "turn_count": telemetry.turn_count,
            "highest_step": telemetry.highest_step,
            "total_attempts": telemetry.total_attempts,
            "attempts_per_step": json.dumps(telemetry.attempts_per_step),
            "failed_criteria": "; ".join(telemetry.failed_criteria),
            "rubric_version": telemetry.rubric_version,
            "prompt_version": telemetry.prompt_version,
            "model": telemetry.model,
        })
    return rows


def _sba_responses(participants) -> list[tuple[str, str, str]]:
    """(participant_id, arm, text) for every written SBA response."""
    found = []
    for participant in participants:
        result = participant.responses.get(Phase.SBA)
        if result is None:
            continue
        text = " ".join(str(v).strip() for v in result.answers.values()).strip()
        if text:
            found.append((participant.participant_id, participant.arm.value, text))
    return found


def _manifest(store, participants, now) -> dict:
    """Provenance. What produced these files, and under what versions.

    The eval harness stamps every run this way and sessions are meant to as
    well; an export without it is a set of numbers nobody can trace back.
    """
    config = store.config
    stamp = config.stamp() if hasattr(config, "stamp") else {}

    counts = {arm.value: 0 for arm in Arm}
    for participant in participants:
        counts[participant.arm.value] += 1

    return {
        "exported_at": _iso(now),
        "participants": len(participants),
        "by_arm": counts,
        "completed": sum(
            1 for p in participants if p.state.phase is Phase.DONE
        ),
        "trial": stamp,
        "note": (
            "Keyed to participant_id. Identity is held separately and is not "
            "read by the export (§4.6.6, §4.7.4). No threshold has been applied: "
            "the §4.6.3 exclusion cutoffs are derived from the pilot and belong "
            "to the analysis, not to these files."
        ),
    }


# --- writing --------------------------------------------------------------


def _write(directory: Path, name: str, rows: list[dict]) -> str:
    """Write one CSV. An empty table still gets a file, with its headers.

    A missing file is ambiguous — nothing collected, or the export failed? An
    empty one with headers says which.
    """
    path = directory / name
    if not rows:
        path.write_text("", encoding="utf-8")
        return name

    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return name


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.strip().lower()) or "rater"


def main(argv: list[str] | None = None) -> None:
    import sys

    from .api.app import _database_url
    from .api.store import TrialStore
    from .interventions.unguided import OfflineChatBackend
    from .persistence import Repository
    from .senseei_link import FakeSenseeiLink
    from .trial_config import load_trial_config

    args = list(sys.argv[1:] if argv is None else argv)
    raters: tuple[str, ...] = ()
    if "--raters" in args:
        index = args.index("--raters")
        raters = tuple(r.strip() for r in args[index + 1].split(",") if r.strip())
        del args[index:index + 2]

    directory = args[0] if args else "export"

    config = load_trial_config()
    store = TrialStore(
        config,
        chat_backend=OfflineChatBackend(),
        repository=Repository(_database_url()),
    )
    store.reload()

    link = FakeSenseeiLink(
        base_url=config.senseei_base_url or "https://senseei.example/session"
    )
    result = export_analysis(store, directory, link=link)
    print(f"Wrote {len(result.files)} files to {result.directory.resolve()} "
          f"({result.participants} participants, {result.sba_responses} SBA responses)")

    if raters:
        blind = export_for_raters(store, raters, directory)
        print(f"Wrote {len(blind.files)} blind grading files for "
              f"{', '.join(raters)} ({blind.sba_responses} responses each)")


if __name__ == "__main__":
    main()
