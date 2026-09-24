"""Turning an uploaded PDF into text, and putting figure descriptions into it.

No database and no provider: extraction runs on the seed's real PDFs, and
placement and parsing on plain data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.figures import Figure, parse_figures
from backend.services.library_service import place_figures
from backend.services.pdf_text import NotAPdf, extract_pages_text, to_text

FIXTURES = Path(__file__).resolve().parent.parent / "scripts" / "fixtures" / "readings"


@pytest.fixture(scope="module")
def tennis() -> str:
    return to_text(extract_pages_text((FIXTURES / "tennis_recovery.pdf").read_bytes()))


def test_paragraphs_survive_as_paragraphs(tennis):
    paragraphs = tennis.split("\n\n")
    opening = next(p for p in paragraphs if p.startswith("Between one shot"))
    # one paragraph, rejoined across its wrapped lines, ending where it ends
    assert opening.endswith("the answer is not the middle of the court.")
    assert "\n" not in opening


def test_page_numbers_and_diagram_labels_are_dropped(tennis):
    paragraphs = tennis.split("\n\n")
    assert "113" not in paragraphs
    assert "net" not in paragraphs and "ball" not in paragraphs


def test_captions_are_kept(tennis):
    assert any(p.startswith("Figure 6.4 The reply cone and its bisector") for p in tennis.split("\n\n"))


def test_a_file_that_is_not_a_pdf_is_refused():
    with pytest.raises(NotAPdf):
        extract_pages_text(b"%PDF-1.4 this is not really a pdf")


# --------------------------------------------------------------------------- #
# placing figure descriptions


PAGES = [
    ["Intro paragraph.", "Figure 1. The five forces", "After the figure."],
    ["Second page.", "Table 2 Ratings by force and more words"],
]


def test_a_description_goes_just_before_its_caption():
    placed = place_figures(
        PAGES, [Figure(description="Five boxes.", label="Figure 1", caption="Figure 1. The five forces", page=1)]
    )
    assert placed[0] == [
        "Intro paragraph.",
        "[Figure 1: Five boxes.]",
        "Figure 1. The five forces",
        "After the figure.",
    ]


def test_a_caption_is_found_by_its_opening_words_even_on_the_wrong_page():
    placed = place_figures(
        PAGES, [Figure(description="Rated.", label="Table 2", caption="Table 2 Ratings by force", page=1)]
    )
    assert placed[1] == ["Second page.", "[Table 2: Rated.]", "Table 2 Ratings by force and more words"]


def test_a_figure_without_a_caption_goes_at_the_end_of_its_page():
    placed = place_figures(PAGES, [Figure(description="A photo.", page=1)])
    assert placed[0][-1] == "[Figure 1: A photo.]"


def test_placing_does_not_change_the_input():
    place_figures(PAGES, [Figure(description="x", page=1)])
    assert len(PAGES[0]) == 3


# --------------------------------------------------------------------------- #
# reading the model's answer


def test_the_models_json_is_read_even_inside_a_code_fence():
    raw = '```json\n{"figures": [{"page": 2, "label": "Figure 1", "caption": null, "description": " Two  boxes. "}]}\n```'
    assert parse_figures(raw) == [Figure(description="Two boxes.", label="Figure 1", caption=None, page=2)]


def test_entries_without_a_description_are_skipped():
    assert parse_figures('{"figures": [{"label": "Figure 1", "description": ""}]}') == []


def test_an_answer_that_is_not_json_is_an_error():
    with pytest.raises(ValueError):
        parse_figures("Here are the figures: none")
