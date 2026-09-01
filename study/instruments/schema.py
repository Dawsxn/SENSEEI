"""What an instrument is: the shape every survey in the trial shares.

The five instruments — demographics, pre-test, post-test Part A, the SBA, and the
SUS — are content, not code. They live as YAML in ``content/`` and are rendered by
one generic renderer. Three things follow from that, and each is the reason for a
field below.

**Faculty review reads what the tool serves.** Section 4.6.4 requires the
pre-test, post-test Part A, and the SBA case to be "reviewed for content validity
by two RVRCOB faculty members prior to administration". If the reviewed document
and the served survey were two artefacts, they would drift, and the review would
end up certifying a document nobody sat. Here the review document is generated
from the same file the participant is shown, so they cannot disagree. The
``status`` field records whether that review has happened, and a live run is
refused while any instrument is still a draft.

**The pre-test / post-test pairing is declared, not implied.** Section 4.6.4 calls
Part A "directly related to the pre-test", and the retention comparison depends on
knowing which post-test item answers which pre-test item. ``pairs_with`` states
it, so the analysis reads a fact rather than a naming convention.

**Attention checks are marked with their expected answer.** Section 4.6.3 embeds
them in the surveys and excludes anyone who fails. Marking them in the content
means the check travels with the item it hides among, rather than living in a
list somewhere that has to be kept in step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ItemType(str, Enum):
    """How an item is answered, which is also how it is rendered."""

    #: A point on a labelled scale. Familiarity ratings and every SUS item.
    LIKERT = "likert"
    #: One option from several. Factual items, and most attention checks.
    MULTIPLE_CHOICE = "multiple_choice"
    #: A line of text: year level, course.
    SHORT_TEXT = "short_text"
    #: A written response. The SBA.
    LONG_TEXT = "long_text"


class Polarity(str, Enum):
    """Which direction agreement points, for scales that mix both.

    The SUS alternates deliberately, so that a participant agreeing with
    everything scores in the middle rather than at the top. Its composite cannot
    be computed without knowing which way each item runs.
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"


class Status(str, Enum):
    """Whether this instrument has passed content-validity review (§4.6.4)."""

    DRAFT = "draft"
    REVIEWED = "reviewed"


@dataclass(frozen=True)
class Option:
    """One choice on a multiple-choice item or a point on a Likert scale."""

    id: str
    text: str


@dataclass(frozen=True)
class Item:
    """One question."""

    id: str
    type: ItemType
    text: str

    options: tuple[Option, ...] = ()
    required: bool = True

    #: The correct option id, for a factual item that is scored. None for items
    #: with no right answer — demographics, familiarity ratings, the SUS.
    answer: str | None = None

    #: The pre-test item this post-test item is paired to (§4.6.4).
    pairs_with: str | None = None

    #: The option id an attentive participant selects. Set only on attention
    #: checks (§4.6.3).
    attention_expected: str | None = None

    #: Which way agreement runs. Required on SUS items, ignored elsewhere.
    polarity: Polarity | None = None

    #: Marks a familiarity rating used for eligibility screening (§4.6.3):
    #: participants must not have previously studied the concept.
    screening: bool = False

    #: Shown under the item text.
    help_text: str = ""

    @property
    def is_attention_check(self) -> bool:
        return self.attention_expected is not None

    @property
    def is_scored(self) -> bool:
        """Whether this item has a right answer worth counting."""
        return self.answer is not None

    @property
    def option_ids(self) -> tuple[str, ...]:
        return tuple(o.id for o in self.options)

    def is_correct(self, given: str | None) -> bool:
        return self.answer is not None and given == self.answer

    def passed_attention(self, given: str | None) -> bool:
        return self.attention_expected is not None and given == self.attention_expected


@dataclass(frozen=True)
class Instrument:
    """One survey, as served and as reviewed."""

    id: str
    title: str
    #: The phase this instrument belongs to, as a plain string so the content
    #: files do not have to import the phase enum.
    phase: str
    version: int = 1
    status: Status = Status.DRAFT

    instructions: str = ""

    #: Material the participant reads before answering — the SBA's business case.
    #: Kept on the instrument rather than as an item because it is not answered.
    stimulus: str = ""

    items: tuple[Item, ...] = field(default_factory=tuple)

    #: Whether the composite of §4.6.5 applies. Set on the SUS alone.
    scoring: str = ""

    #: Free-text note carried into the review document, e.g. the source of a
    #: standardised instrument.
    source: str = ""

    @property
    def is_reviewed(self) -> bool:
        return self.status is Status.REVIEWED

    @property
    def attention_checks(self) -> tuple[Item, ...]:
        return tuple(i for i in self.items if i.is_attention_check)

    @property
    def scored_items(self) -> tuple[Item, ...]:
        return tuple(i for i in self.items if i.is_scored)

    @property
    def screening_items(self) -> tuple[Item, ...]:
        return tuple(i for i in self.items if i.screening)

    @property
    def answerable_items(self) -> tuple[Item, ...]:
        """Items a participant actually answers, attention checks included."""
        return self.items

    def item(self, item_id: str) -> Item | None:
        for candidate in self.items:
            if candidate.id == item_id:
                return candidate
        return None

    @property
    def is_placeholder(self) -> bool:
        """Whether this is still a stub awaiting its real content.

        The pre-test, post-test A, and the SBA cannot be written until the trial
        reading is chosen, so they ship as stubs. A live run is refused while any
        remain, alongside the review check — an unwritten instrument and an
        unreviewed one are both reasons not to collect data yet.
        """
        return not self.items and not self.stimulus


class InstrumentError(ValueError):
    """An instrument's content is not usable as written."""
