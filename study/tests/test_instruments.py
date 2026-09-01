"""The instruments: their validation, their scoring, and the review document."""

from __future__ import annotations

import pytest

from study.instruments import load_all, load_instrument, readiness, score
from study.instruments.loader import CONTENT_DIR, INSTRUMENT_ORDER, validate_pairings
from study.instruments.review import render
from study.instruments.schema import InstrumentError, Polarity, Status
from study.instruments.scoring import sus_composite


@pytest.fixture
def instruments():
    return load_all()


def write(tmp_path, body: str):
    path = tmp_path / "thing.yaml"
    path.write_text(body, encoding="utf-8")
    return path


# --- what ships -----------------------------------------------------------


def test_every_instrument_in_table_4_11_has_a_file(instruments):
    assert {i.id for i in instruments.values()} == set(INSTRUMENT_ORDER)


def test_the_content_files_all_load(instruments):
    """Validation runs on load, so this failing means one is malformed."""
    assert len(instruments) == 5


def test_the_three_reading_dependent_instruments_are_still_stubs(instruments):
    """They cannot be written until the trial reading is chosen."""
    for name in ("pre_test", "post_test_a", "sba"):
        assert instruments[name].is_placeholder


def test_readiness_reports_what_blocks_collection(instruments):
    outstanding = " ".join(readiness(instruments))

    assert "pre_test: no content" in outstanding
    assert "demographics: not marked reviewed" in outstanding


def test_the_sus_needs_no_content_review(instruments):
    """A standardised instrument is not the researchers' to validate."""
    assert instruments["sus"].status is Status.REVIEWED
    assert "not subject to" in instruments["sus"].source


# --- validation that prevents silently meaningless data -------------------


def test_an_unreachable_correct_answer_is_refused(tmp_path):
    """An answer outside the options can never be scored correct."""
    path = write(tmp_path, """
id: t
title: t
items:
  - id: q1
    type: multiple_choice
    text: q
    answer: z
    options:
      - {id: a, text: A}
      - {id: b, text: B}
""")
    with pytest.raises(InstrumentError, match="never be scored correct"):
        load_instrument(path)


def test_an_unpassable_attention_check_is_refused(tmp_path):
    """§4.6.3 excludes on failure, so every participant would be excluded."""
    path = write(tmp_path, """
id: t
title: t
items:
  - id: q1
    type: multiple_choice
    text: q
    attention_check: {expected: z}
    options:
      - {id: a, text: A}
""")
    with pytest.raises(InstrumentError, match="every participant would fail"):
        load_instrument(path)


def test_a_sus_item_without_a_polarity_is_refused(tmp_path):
    """A flipped polarity yields a wrong score that still looks plausible."""
    path = write(tmp_path, """
id: t
title: t
scoring: sus
items:
  - id: q1
    type: likert
    text: q
    options:
      - {id: "1", text: One}
""")
    with pytest.raises(InstrumentError, match="needs a polarity"):
        load_instrument(path)


def test_a_choice_item_without_options_is_refused(tmp_path):
    path = write(tmp_path, """
id: t
title: t
items:
  - {id: q1, type: multiple_choice, text: q}
""")
    with pytest.raises(InstrumentError, match="needs options"):
        load_instrument(path)


def test_duplicate_item_ids_are_refused(tmp_path):
    path = write(tmp_path, """
id: t
title: t
items:
  - {id: q1, type: short_text, text: a}
  - {id: q1, type: short_text, text: b}
""")
    with pytest.raises(InstrumentError, match="more than once"):
        load_instrument(path)


def test_a_dangling_pretest_pairing_is_caught(tmp_path):
    """§4.6.4's retention comparison depends on the pairing resolving."""
    pre = write(tmp_path, """
id: pre_test
phase: pre_test
title: pre
items:
  - {id: known, type: short_text, text: q}
""")
    post = tmp_path / "post.yaml"
    post.write_text("""
id: post_test_a
phase: post_test_a
title: post
items:
  - {id: p1, type: short_text, text: q, pairs_with: missing}
""", encoding="utf-8")

    problems = validate_pairings(
        {"pre_test": load_instrument(pre), "post_test_a": load_instrument(post)}
    )
    assert problems and "not a pre-test item" in problems[0]


def test_a_resolving_pairing_passes(tmp_path):
    pre = write(tmp_path, """
id: pre_test
phase: pre_test
title: pre
items:
  - {id: known, type: short_text, text: q}
""")
    post = tmp_path / "post.yaml"
    post.write_text("""
id: post_test_a
phase: post_test_a
title: post
items:
  - {id: p1, type: short_text, text: q, pairs_with: known}
""", encoding="utf-8")

    assert validate_pairings(
        {"pre_test": load_instrument(pre), "post_test_a": load_instrument(post)}
    ) == []


# --- scoring --------------------------------------------------------------


@pytest.fixture
def quiz(tmp_path):
    return load_instrument(write(tmp_path, """
id: quiz
title: quiz
items:
  - id: q1
    type: multiple_choice
    text: q1
    answer: a
    options:
      - {id: a, text: A}
      - {id: b, text: B}
  - id: q2
    type: multiple_choice
    text: q2
    answer: b
    options:
      - {id: a, text: A}
      - {id: b, text: B}
  - id: attn
    type: multiple_choice
    text: Choose B for this one.
    attention_check: {expected: b}
    options:
      - {id: a, text: A}
      - {id: b, text: B}
"""))


def test_correct_answers_are_counted(quiz):
    result = score(quiz, {"q1": "a", "q2": "b", "attn": "b"})
    assert (result.correct, result.scored) == (2, 2)


def test_an_attention_check_is_not_a_factual_item(quiz):
    """It tests whether they are reading, not whether they know anything."""
    result = score(quiz, {"q1": "a", "q2": "b", "attn": "b"})
    assert result.scored == 2


def test_a_failed_attention_check_is_recorded(quiz):
    result = score(quiz, {"q1": "a", "q2": "b", "attn": "a"})
    assert result.failed_attention_check
    assert (result.attention_failed, result.attention_answered) == (1, 1)


def test_a_passed_attention_check_is_not_a_failure(quiz):
    assert not score(quiz, {"q1": "a", "q2": "b", "attn": "b"}).failed_attention_check


def test_a_blank_is_not_counted_as_wrong(quiz):
    """Absence of evidence must not look like a mistaken answer."""
    result = score(quiz, {"q1": "a"})
    assert result.correct == 1
    assert "q2" in result.missing


def test_an_incomplete_submission_is_flagged(quiz):
    assert not score(quiz, {"q1": "a"}).is_complete
    assert score(quiz, {"q1": "a", "q2": "b", "attn": "b"}).is_complete


def test_whitespace_only_counts_as_unanswered(quiz):
    assert "q1" in score(quiz, {"q1": "   "}).missing


def test_a_screening_answer_is_kept(instruments):
    """§4.6.3: eligibility turns on not having studied the concept before."""
    result = score(instruments["demographics"],
                   {"year_level": "3", "department": "MOD", "prior_course": "yes"})
    assert result.screening == {"prior_course": "yes"}


# --- the SUS composite ----------------------------------------------------


def test_the_sus_composite_runs_zero_to_one_hundred(instruments):
    sus = instruments["sus"]
    worst = {
        i.id: ("1" if i.polarity is Polarity.POSITIVE else "5") for i in sus.items
    }
    best = {
        i.id: ("5" if i.polarity is Polarity.POSITIVE else "1") for i in sus.items
    }

    assert sus_composite(sus, worst) == 0.0
    assert sus_composite(sus, best) == 100.0


@pytest.mark.parametrize("everything", ["1", "3", "5"])
def test_straight_lining_lands_mid_scale(instruments, everything):
    """The alternating polarity is the instrument: agreeing with all ten of a
    mixed-polarity scale is not a rave review."""
    sus = instruments["sus"]
    assert sus_composite(sus, {i.id: everything for i in sus.items}) == 50.0


def test_a_partial_sus_has_no_composite(instruments):
    """The scale is defined over all ten items; scaling a subset would produce a
    number that is not a SUS score while looking exactly like one."""
    sus = instruments["sus"]
    answers = {i.id: "4" for i in sus.items}
    answers.pop("sus7")

    assert sus_composite(sus, answers) is None


def test_only_the_sus_gets_a_composite(instruments, quiz):
    assert score(quiz, {"q1": "a"}).sus_score is None
    assert score(instruments["demographics"], {}).sus_score is None


def test_the_sus_alternates_polarity(instruments):
    """Five each way, as published."""
    polarities = [i.polarity for i in instruments["sus"].items]
    assert polarities.count(Polarity.POSITIVE) == 5
    assert polarities.count(Polarity.NEGATIVE) == 5


# --- the review document --------------------------------------------------


def test_the_review_document_renders(instruments):
    assert "<html>" in render(instruments)


def test_the_review_document_shows_reviewers_the_hidden_material(tmp_path):
    """Correct answers, checks and pairings are what a content review judges."""
    instrument = load_instrument(write(tmp_path, """
id: pre_test
phase: pre_test
title: Pre-test
items:
  - id: q1
    type: multiple_choice
    text: Which is a switching cost?
    answer: b
    options:
      - {id: a, text: The price}
      - {id: b, text: Retraining staff}
  - id: attn
    type: multiple_choice
    text: Choose the second option.
    attention_check: {expected: b}
    options:
      - {id: a, text: First}
      - {id: b, text: Second}
"""))
    page = render({"pre_test": instrument})

    assert "correct" in page
    assert "attention check" in page
    assert "expected" in page


def test_the_review_document_lists_what_is_outstanding(instruments):
    assert "Outstanding" in render(instruments)


def test_the_review_document_escapes_content(tmp_path):
    instrument = load_instrument(write(tmp_path, """
id: t
title: t
items:
  - {id: q1, type: short_text, text: "<script>alert(1)</script>"}
"""))
    assert "<script>alert(1)</script>" not in render({"t": instrument})


def test_the_review_document_is_generated_from_the_served_content():
    """Not transcribed alongside it, so the two cannot drift apart."""
    page = render()
    assert CONTENT_DIR.name in page


def test_the_review_document_is_written_as_utf8(tmp_path):
    """A Windows shell redirect encodes stdout as cp1252 and mangles every em
    dash and section sign. The reviewers would be the ones to find out."""
    from study.instruments.review import write

    path = write(tmp_path / "out" / "review.html")

    assert path.exists()
    assert "—" in path.read_text(encoding="utf-8")


# --- the worked example set -----------------------------------------------


def test_the_example_set_is_complete_and_consistent():
    """It doubles as the template for the real instruments, so it must be a
    model of a finished set — every pairing resolving, nothing outstanding."""
    from study.instruments.loader import EXAMPLE_DIR

    example = load_all(EXAMPLE_DIR)

    assert readiness(example) == []
    assert validate_pairings(example) == []


def test_every_example_factual_post_test_item_answers_a_pretest_item():
    from study.instruments.loader import EXAMPLE_DIR

    example = load_all(EXAMPLE_DIR)
    pre_ids = {i.id for i in example["pre_test"].items}

    paired = [i for i in example["post_test_a"].items if i.pairs_with]
    assert paired
    assert all(i.pairs_with in pre_ids for i in paired)


def test_the_example_sba_never_names_the_concept():
    """Naming it turns transfer into retrieval: the participant would know
    which tool to reach for rather than having to recognise the need for it."""
    from study.instruments.loader import EXAMPLE_DIR

    sba = load_all(EXAMPLE_DIR)["sba"]
    shown = (sba.stimulus + " " + " ".join(i.text for i in sba.items)).lower()

    assert "switching cost" not in shown


def test_the_example_set_is_not_what_the_app_serves():
    """A sample must never be mistaken for the trial's real instruments."""
    from study.instruments.loader import EXAMPLE_DIR

    assert EXAMPLE_DIR != CONTENT_DIR
    assert load_all()["pre_test"].is_placeholder
