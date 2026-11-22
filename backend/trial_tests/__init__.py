"""The trial's pre-tests and post-tests, one YAML file per reading.

A test lives in the code, not the database, so it changes only through a
release, and nothing is released between sittings (docs/context/trial.md). A
class takes a test when its "Pre-test and post-test" setting names the test's
key, which is offered only when the class's reading has the test's exact title.

`load()` reads every file once and checks it, so a mistake in a test (a choice
answer that is not one of the options, a rubric that skips a score) stops the
app at startup rather than surfacing in the middle of a sitting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

#: The two tests a participant takes, in this order.
PRE, POST = "pre", "post"
WHICH = (PRE, POST)
#: The pre-test's single question, as an item id.
PRE_ITEM = "pre"

#: choice: one option, 1 point. truefalse: a set of statements, 1 point each.
#: text: written, graded by hand. steps: written in parts, one score by hand.
KINDS = ("choice", "truefalse", "text", "steps")


@dataclass(frozen=True)
class Statement:
    """One statement in a true/false set. `why` is for the answer key only."""

    text: str
    answer: bool
    why: str = ""


@dataclass(frozen=True)
class Item:
    id: str
    kind: str                       # one of KINDS
    question: str
    part: str = ""                  # A to D; the pre-test has none
    dimension: str = ""
    options: dict[str, str] = field(default_factory=dict)
    answer: str | None = None       # choice only
    why: str = ""
    goal: str = ""
    reference: str = ""
    criteria: dict[int, str] = field(default_factory=dict)
    examples: dict[int, str] = field(default_factory=dict)
    scored: bool = True
    statements: dict[str, Statement] = field(default_factory=dict)  # truefalse
    steps: dict[str, str] = field(default_factory=dict)             # steps: part -> prompt
    lock_first: bool = False                                        # steps

    @property
    def points(self) -> int:
        """What full marks are worth: 1 for a choice, 1 per statement in a
        true/false set, the top criterion for anything written."""
        if not self.scored:
            return 0
        if self.kind == "choice":
            return 1
        if self.kind == "truefalse":
            return len(self.statements)
        return max(self.criteria)

    @property
    def ticked(self) -> bool:
        """Whether it ends with "I'm sure / I'm not sure": parts A to C."""
        return self.part in ("A", "B", "C")

    @property
    def graded_by_hand(self) -> bool:
        return self.scored and self.kind in ("text", "steps")


@dataclass(frozen=True)
class Test:
    key: str
    reading_title: str
    pretest_minutes: int
    posttest_minutes: int
    #: A line shown at the start of a part, under its heading.
    part_intros: dict[str, str]
    pretest: Item
    posttest: tuple[Item, ...]

    def items(self, which: str) -> tuple[Item, ...]:
        return (self.pretest,) if which == PRE else self.posttest

    def item(self, which: str, item_id: str) -> Item | None:
        return next((i for i in self.items(which) if i.id == item_id), None)

    def total(self, which: str) -> int:
        return sum(i.points for i in self.items(which))


class InvalidTest(Exception):
    """A test file is wrong; the message says where."""


def _item(raw: dict, where: str) -> Item:
    kind = raw.get("kind")
    if kind not in KINDS:
        raise InvalidTest(f"{where}: kind must be one of {KINDS}")
    item = Item(
        id=str(raw["id"]),
        kind=kind,
        question=raw["question"].strip(),
        part=raw.get("part", ""),
        dimension=raw.get("dimension", ""),
        options={str(k): v for k, v in (raw.get("options") or {}).items()},
        answer=raw.get("answer"),
        why=raw.get("why", ""),
        goal=raw.get("goal", ""),
        reference=raw.get("reference", ""),
        criteria={int(k): v for k, v in (raw.get("criteria") or {}).items()},
        examples={int(k): v for k, v in (raw.get("examples") or {}).items()},
        scored=raw.get("scored", True),
        statements={
            str(k): Statement(
                text=" ".join(str(v["text"]).split()),
                answer=v["answer"],
                why=v.get("why", ""),
            )
            for k, v in (raw.get("statements") or {}).items()
        },
        steps={str(k): " ".join(str(v).split()) for k, v in (raw.get("steps") or {}).items()},
        lock_first=bool(raw.get("lock_first", False)),
    )
    if kind == "choice" and item.answer not in item.options:
        raise InvalidTest(f"{where}: the answer {item.answer!r} is not one of the options")
    if kind == "truefalse" and (
        not item.statements or any(not isinstance(st.answer, bool) for st in item.statements.values())
    ):
        raise InvalidTest(f"{where}: a true/false set needs statements, each answered true or false")
    if kind == "steps" and len(item.steps) < 2:
        raise InvalidTest(f"{where}: a question in steps needs at least two parts")
    if item.graded_by_hand and sorted(item.criteria) != list(range(max(item.criteria or [0]) + 1)):
        raise InvalidTest(f"{where}: criteria must run from 0 to the item's points")
    return item


def _test(path: Path) -> Test:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    pre = raw["pretest"]
    test = Test(
        key=raw["key"],
        reading_title=raw["reading_title"].strip(),
        pretest_minutes=int(raw["pretest_minutes"]),
        posttest_minutes=int(raw["posttest_minutes"]),
        part_intros={str(k): v for k, v in (raw.get("part_intros") or {}).items()},
        pretest=_item({"id": PRE_ITEM, "kind": "text", **pre}, f"{path.name} pretest"),
        posttest=tuple(
            _item(r, f"{path.name} {r.get('id')}") for r in raw["posttest"]
        ),
    )
    ids = [i.id for i in test.posttest]
    if len(set(ids)) != len(ids):
        raise InvalidTest(f"{path.name}: two post-test items share an id")
    return test


@lru_cache
def load() -> dict[str, Test]:
    """Every test, by key."""
    tests = {}
    for path in sorted(HERE.glob("*.yaml")):
        test = _test(path)
        if test.key in tests:
            raise InvalidTest(f"two tests have the key {test.key!r}")
        tests[test.key] = test
    return tests


def get(key: str | None) -> Test | None:
    return load().get(key) if key else None


def for_title(title: str) -> list[Test]:
    """The tests written for a reading with this exact title."""
    return [t for t in load().values() if t.reading_title == title.strip()]
