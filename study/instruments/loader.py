"""Reading the instrument content, and refusing content that cannot be trusted.

Validation here is not defensive tidying. Each check corresponds to a way the
study could produce data that looks fine and means nothing:

- An attention check whose expected answer is not one of its options can never be
  passed, so every participant would be excluded (§4.6.3).
- A scored item whose answer is not one of its options is never correct, so it
  silently depresses every score.
- A ``pairs_with`` pointing at a pre-test item that does not exist breaks the
  retention comparison, and would be discovered during analysis.
- A SUS item without a polarity makes the composite uncomputable, and guessing a
  direction would invert half the scale.

All of these are cheap to catch now and expensive to catch later, so the loader
raises rather than warns.
"""

from __future__ import annotations

from pathlib import Path

from .schema import (
    Instrument,
    InstrumentError,
    Item,
    ItemType,
    Option,
    Polarity,
    Status,
)

CONTENT_DIR = Path(__file__).parent / "content"

#: The five instruments of Table 4.11, in the order a participant meets them.
INSTRUMENT_ORDER = ("demographics", "pre_test", "post_test_a", "sba", "sus")


def load_instrument(path: str | Path) -> Instrument:
    """Read and validate one instrument file."""
    import yaml

    path = Path(path)
    if not path.exists():
        raise InstrumentError(f"No instrument at {path}.")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = tuple(_build_item(raw, path) for raw in (data.get("items") or []))

    instrument = Instrument(
        id=str(data.get("id") or path.stem),
        title=str(data.get("title", "")),
        phase=str(data.get("phase") or path.stem),
        version=int(data.get("version", 1)),
        status=Status(str(data.get("status", "draft")).lower()),
        instructions=str(data.get("instructions", "")),
        stimulus=str(data.get("stimulus", "")),
        items=items,
        scoring=str(data.get("scoring", "")),
        source=str(data.get("source", "")),
    )
    _validate(instrument, path)
    return instrument


def load_all(directory: str | Path | None = None) -> dict[str, Instrument]:
    """Load every instrument, keyed by phase, in the order of Table 4.11."""
    directory = Path(directory) if directory else CONTENT_DIR
    loaded: dict[str, Instrument] = {}
    for name in INSTRUMENT_ORDER:
        path = directory / f"{name}.yaml"
        if path.exists():
            instrument = load_instrument(path)
            loaded[instrument.phase] = instrument
    return loaded


def _build_item(raw: dict, path: Path) -> Item:
    item_id = str(raw.get("id") or "")
    if not item_id:
        raise InstrumentError(f"{path}: an item has no id.")

    try:
        item_type = ItemType(str(raw.get("type", "multiple_choice")))
    except ValueError as exc:
        raise InstrumentError(
            f"{path}: item {item_id!r} has unknown type {raw.get('type')!r}."
        ) from exc

    options = tuple(
        Option(id=str(o["id"]), text=str(o.get("text", "")))
        for o in (raw.get("options") or [])
    )

    polarity = raw.get("polarity")
    attention = raw.get("attention_check") or {}

    return Item(
        id=item_id,
        type=item_type,
        text=str(raw.get("text", "")),
        options=options,
        required=bool(raw.get("required", True)),
        answer=_as_str_or_none(raw.get("answer")),
        pairs_with=_as_str_or_none(raw.get("pairs_with")),
        attention_expected=_as_str_or_none(attention.get("expected")),
        polarity=Polarity(str(polarity)) if polarity else None,
        screening=bool(raw.get("screening", False)),
        help_text=str(raw.get("help_text", "")),
    )


def _as_str_or_none(value) -> str | None:
    return None if value is None else str(value)


def _validate(instrument: Instrument, path: Path) -> None:
    problems: list[str] = []

    seen: set[str] = set()
    for item in instrument.items:
        if item.id in seen:
            problems.append(f"item id {item.id!r} appears more than once")
        seen.add(item.id)

        needs_options = item.type in (ItemType.LIKERT, ItemType.MULTIPLE_CHOICE)
        if needs_options and not item.options:
            problems.append(f"{item.id}: a {item.type.value} item needs options")

        if item.answer is not None and item.answer not in item.option_ids:
            problems.append(
                f"{item.id}: answer {item.answer!r} is not one of its options "
                f"{list(item.option_ids)} — the item could never be scored correct"
            )

        if (
            item.attention_expected is not None
            and item.attention_expected not in item.option_ids
        ):
            problems.append(
                f"{item.id}: attention check expects {item.attention_expected!r}, "
                f"not among {list(item.option_ids)} — every participant would fail it"
            )

    if instrument.scoring == "sus":
        for item in instrument.items:
            if item.polarity is None:
                problems.append(
                    f"{item.id}: a SUS item needs a polarity, or the composite "
                    "cannot be computed"
                )

    if problems:
        raise InstrumentError(
            f"{path} is not usable:\n  - " + "\n  - ".join(problems)
        )


def validate_pairings(instruments: dict[str, Instrument]) -> list[str]:
    """Check every ``pairs_with`` points at a real pre-test item (§4.6.4).

    Cross-file, so it cannot run inside a single instrument's own validation.
    Returns the problems rather than raising, because the pre-test may legitimately
    be a stub while the post-test is being drafted.
    """
    pre_test = instruments.get("pre_test")
    post_test = instruments.get("post_test_a")
    if pre_test is None or post_test is None or pre_test.is_placeholder:
        return []

    known = {item.id for item in pre_test.items}
    return [
        f"{item.id} pairs with {item.pairs_with!r}, which is not a pre-test item"
        for item in post_test.items
        if item.pairs_with and item.pairs_with not in known
    ]


def readiness(instruments: dict[str, Instrument]) -> list[str]:
    """What still stands between these instruments and real data collection.

    Two separate gates. An instrument with no content cannot be administered at
    all, and an instrument that has not been through the content-validity review
    of §4.6.4 must not be. Both are reported, because they are fixed by different
    people at different times.
    """
    problems: list[str] = []

    for name in INSTRUMENT_ORDER:
        instrument = next(
            (i for i in instruments.values() if i.id == name), None
        )
        if instrument is None:
            problems.append(f"{name}: no instrument file")
        elif instrument.is_placeholder:
            problems.append(f"{name}: no content written yet")
        elif not instrument.is_reviewed:
            problems.append(
                f"{name}: not marked reviewed — §4.6.4 requires content-validity "
                "review by two RVRCOB faculty before administration"
            )

    problems.extend(validate_pairings(instruments))
    return problems
