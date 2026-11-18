import csv
import hashlib
import re

import pytest

from src import versions
from src.versions import VersionError


def prompts(base):
    return base.parent / "agents" / "prompts"


def rubrics(base):
    return base.parent / "agents" / "rubrics"


def prompt_text(base, n=3):
    return versions.read_version(base, "prompt", n)


def rubric_text(base):
    return versions.read_version(base, "rubric", 3)


def test_lists_versions_and_numbers_the_next_one_after_the_highest(base):
    assert versions.list_versions(base, "prompt") == [3]
    assert versions.next_version(base, "prompt") == 4
    (prompts(base) / "system_prompt_v7.md").write_text("x {{RUBRIC}}", encoding="utf-8")
    assert versions.list_versions(base, "prompt") == [3, 7]
    assert versions.next_version(base, "prompt") == 8      # max + 1, never fills the gap


def test_tutor_and_figure_prompts_in_the_same_folder_are_not_versions(base):
    (prompts(base) / "figure_prompt_v9.md").write_text("x", encoding="utf-8")
    assert versions.list_versions(base, "prompt") == [3]   # tutor_prompt_v2.md is there too
    assert versions.next_version(base, "prompt") == 4


def test_versions_live_in_the_agents_package_beside_the_eval_folder(base):
    assert versions.path_for(base, "prompt", 3) == (prompts(base) / "system_prompt_v3.md").resolve()
    assert versions.path_for(base, "rubric", 3) == (rubrics(base) / "rubric_v3.yaml").resolve()


def test_save_creates_the_next_version_and_never_touches_the_old_one(base):
    before = (prompts(base) / "system_prompt_v3.md").read_bytes()
    n = versions.save_version(base, "prompt", prompt_text(base) + "\nBe kind.\n", based_on=3,
                              note="soften tone")
    assert n == 4
    saved = (prompts(base) / "system_prompt_v4.md").read_text(encoding="utf-8")
    assert saved.endswith("Be kind.\n") and "\r" not in saved
    assert (prompts(base) / "system_prompt_v3.md").read_bytes() == before
    assert versions.save_version(base, "prompt", saved + "More.\n", based_on=4) == 5


def test_saving_never_changes_what_is_pinned(base):
    config_before = (base / "config.yaml").read_bytes()
    tutor_before = (prompts(base) / "tutor_prompt_v2.md").read_bytes()
    versions.save_version(base, "prompt", prompt_text(base) + "x\n", based_on=3)
    versions.save_version(base, "rubric", rubric_text(base).replace("not vague.", "not vague at all."),
                          based_on=3)
    assert (base / "config.yaml").read_bytes() == config_before
    assert (prompts(base) / "tutor_prompt_v2.md").read_bytes() == tutor_before
    assert versions.pinned(base)["prompt"] == {3: ["config.yaml"]}


def test_save_records_who_it_was_based_on_and_the_note(base):
    versions.save_version(base, "prompt", prompt_text(base) + "x\n", based_on=3, note="try x")
    rows = list(csv.DictReader(open(prompts(base) / "versions.csv", encoding="utf-8", newline="")))
    assert len(rows) == 1
    assert rows[0]["version"] == "v4" and rows[0]["based_on"] == "v3" and rows[0]["note"] == "try x"
    assert rows[0]["saved_at"]


def test_unchanged_text_is_refused_even_with_different_line_endings(base):
    same = prompt_text(base).replace("\n", "\r\n")
    with pytest.raises(VersionError, match="no changes"):
        versions.save_version(base, "prompt", same, based_on=3)
    assert versions.list_versions(base, "prompt") == [3]


def test_prompt_must_keep_the_rubric_slot_exactly_once(base):
    for bad in (prompt_text(base).replace("{{RUBRIC}}", ""), prompt_text(base) + "\n{{RUBRIC}}\n", "   "):
        with pytest.raises(VersionError):
            versions.save_version(base, "prompt", bad, based_on=3)
    assert versions.list_versions(base, "prompt") == [3]


def test_saving_a_rubric_makes_rubric_v4_independent_of_the_prompt_numbering(base):
    text = rubric_text(base).replace("not vague.", "not vague at all.")
    assert versions.save_version(base, "rubric", text, based_on=3) == 4
    assert (rubrics(base) / "rubric_v4.yaml").exists()
    assert versions.next_version(base, "prompt") == 4


@pytest.mark.parametrize("mutate, message", [
    (lambda t: "State: [unclosed", "YAML"),
    (lambda t: "- just\n- a list\n", "mapping"),
    (lambda t: t.replace("Illustrate:", "Illustrat:"), "Illustrate"),
    (lambda t: t.replace('    pass: "The illustration gives the reader something they can picture in their mind. '
                         'It is concrete and expressive enough to form a mental image."', '    pass: ""'),
     "Imagery"),
])
def test_invalid_rubrics_are_refused_with_a_reason(base, mutate, message):
    with pytest.raises(VersionError, match=message):
        versions.save_version(base, "rubric", mutate(rubric_text(base)), based_on=3)
    assert versions.list_versions(base, "rubric") == [3]


def test_renaming_a_criterion_the_example_set_uses_warns(base):
    result = versions.check(base, "rubric", rubric_text(base).replace("  Brevity:", "  Terseness:"), 3)
    assert result.errors == []
    assert len(result.warnings) == 1
    assert "Brevity" in result.warnings[0] and "example set v3" in result.warnings[0]


def test_a_new_criterion_the_example_set_does_not_mention_is_fine(base):
    # an example set lists only the criteria a row should fail, so an extra criterion is not a gap
    text = rubric_text(base).replace("  Brevity:", '  Tone:\n    pass: "Neutral."\n  Brevity:')
    result = versions.check(base, "rubric", text, 3)
    assert result.errors == [] and result.warnings == []


def test_name_matching_is_as_loose_as_the_eval(base):
    result = versions.check(base, "rubric", rubric_text(base).replace("  Own Words:", "  own-words:"), 3)
    assert result.warnings == []


def test_unchanged_rubric_has_no_warnings_and_reports_no_change(base):
    result = versions.check(base, "rubric", rubric_text(base), 3)
    assert result.errors == [] and result.warnings == [] and result.changed is False


def test_no_readable_example_set_means_no_warnings_not_an_error(base):
    (base / "data" / "example_set_v3.csv").unlink()
    result = versions.check(base, "rubric", rubric_text(base).replace("  Brevity:", "  Terseness:"), 3)
    assert result.errors == [] and result.warnings == []


def test_check_returns_a_readable_diff(base):
    result = versions.check(base, "prompt", prompt_text(base).replace("Be strict, but charge", "Be fair, but charge"), 3)
    assert result.changed and any(l.startswith("-") and "Be strict, but charge" in l for l in result.diff)
    assert any(l.startswith("+") and "Be fair, but charge" in l for l in result.diff)


def test_only_known_kinds_and_integer_versions_are_accepted(base):
    for kind, n in (("config", 3), ("prompt", "../x"), ("prompt", 99), ("prompt", True)):
        with pytest.raises(VersionError):
            versions.read_version(base, kind, n)


def test_pinned_versions_come_from_the_eval_config(base):
    pins = versions.pinned(base)
    assert pins["prompt"][3] == ["config.yaml"]
    assert pins["rubric"][3] == ["config.yaml"]


def test_preview_shows_what_the_model_sees_with_the_rubric_filled_in(base, restore_rubric):
    text, digest = versions.preview(base, prompt_text(base), rubric=3)
    assert "{{RUBRIC}}" not in text and "### STATE" in text and len(digest) == 10


def test_preview_hash_is_computed_the_way_run_eval_computes_it(base, restore_rubric):
    from agents.rubric import load_rubric, render_rubric
    raw = (prompts(base) / "system_prompt_v3.md").read_text(encoding="utf-8")   # as run_eval reads it
    load_rubric(rubrics(base) / "rubric_v3.yaml")
    expected = hashlib.sha256(raw.replace("{{RUBRIC}}", render_rubric()).encode("utf-8")).hexdigest()[:10]
    assert versions.preview(base, raw, rubric=3)[1] == expected


# ---- comparing versions ---------------------------------------------------------------

def make_v4(base, old="Be strict, but charge", new="Be fair, but charge"):
    return versions.save_version(base, "prompt", prompt_text(base).replace(old, new), based_on=3,
                                 note="loosen")


def test_compare_diffs_one_version_against_another_in_that_direction(base):
    make_v4(base)
    c = versions.compare(base, "prompt", 3, 4)
    assert c.changed and c.added == 1 and c.removed == 1
    assert any(l.startswith("-") and "Be strict, but charge" in l for l in c.diff)
    assert any(l.startswith("+") and "Be fair, but charge" in l for l in c.diff)
    flipped = versions.compare(base, "prompt", 4, 3)
    assert any(l.startswith("+") and "Be strict, but charge" in l for l in flipped.diff)


def test_compare_a_version_with_itself_is_no_change(base):
    c = versions.compare(base, "prompt", 3, 3)
    assert not c.changed and c.diff == [] and (c.added, c.removed) == (0, 0)


def test_compare_context_can_cover_the_whole_file(base):
    make_v4(base)
    short = versions.compare(base, "prompt", 3, 4, context=1)
    whole = versions.compare(base, "prompt", 3, 4, context=None)
    assert len(whole.diff) > len(short.diff)
    assert len(whole.diff) >= len(prompt_text(base).splitlines())


def test_compare_rejects_unknown_versions_and_kinds(base):
    with pytest.raises(VersionError):
        versions.compare(base, "prompt", 3, 9)
    with pytest.raises(VersionError):
        versions.compare(base, "config", 3, 3)


def test_version_info_reads_the_save_log_and_calls_unlogged_versions_baseline(base):
    make_v4(base)
    baseline = versions.version_info(base, "prompt", 3)
    assert baseline["logged"] is False and "based_on" not in baseline
    info = versions.version_info(base, "prompt", 4)
    assert info["logged"] and info["based_on"] == 3 and info["note"] == "loosen" and info["saved_at"]


def test_every_version_has_a_created_date_from_the_log_or_the_file(base):
    make_v4(base)
    stamp = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
    assert re.fullmatch(stamp, versions.version_info(base, "prompt", 3)["created"])   # file time
    v4 = versions.version_info(base, "prompt", 4)
    assert v4["created"] == v4["saved_at"] and re.fullmatch(stamp, v4["created"])      # logged time


LOG_COLUMNS = ["timestamp", "prompt_version", "rubric_version", "example_set_version", "model",
               "total", "verdict_accuracy", "criteria_exact_rate", "est_cost_usd", "report_file"]


def write_log(base, rows):
    with open(base / "results_log.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS, restval="")
        w.writeheader()
        w.writerows(rows)


def test_runs_for_lists_logged_runs_of_that_version_only(base):
    write_log(base, [
        {"timestamp": "20261101_100000", "prompt_version": "v3", "rubric_version": "v3",
         "example_set_version": "v3", "model": "gemini-3.1-pro-preview", "total": "71",
         "verdict_accuracy": "0.88", "criteria_exact_rate": "0.6", "est_cost_usd": "0.4",
         "report_file": "r1.html"},
        {"timestamp": "20261102_100000", "prompt_version": "v4", "rubric_version": "v3",
         "example_set_version": "v4", "model": "gemini-3.1-pro-preview", "total": "69",
         "verdict_accuracy": "0.9", "report_file": "r2.html"}])
    v3 = versions.runs_for(base, "prompt", 3)
    assert [r["report_file"] for r in v3] == ["r1.html"]
    assert v3[0]["verdict_accuracy"] == "0.88" and v3[0]["example_set_version"] == "v3"
    assert [r["report_file"] for r in versions.runs_for(base, "prompt", 4)] == ["r2.html"]
    assert [r["report_file"] for r in versions.runs_for(base, "rubric", 3)] == ["r1.html", "r2.html"]


def test_runs_for_reads_the_real_log_format(base):
    from conftest import EVAL
    (base / "results_log.csv").write_bytes((EVAL / "results_log.csv").read_bytes())
    runs = versions.runs_for(base, "prompt", 3)
    assert runs and all(r["total"] and r["verdict_accuracy"] for r in runs)


def test_runs_for_without_a_log_is_empty(base):
    assert versions.runs_for(base, "prompt", 3) == []


def test_an_unlogged_version_in_the_repo_is_dated_by_its_first_commit_not_the_checkout():
    # v1 was written in the eval folder and later moved into agents/; the date follows the move back
    import subprocess
    from conftest import EVAL, REPO
    info = versions.version_info(EVAL, "prompt", 1)   # read-only: nothing is written
    git = subprocess.run(["git", "log", "--diff-filter=A", "--follow", "--format=%cd",
                          "--date=format:%Y-%m-%d %H:%M:%S", "--", "agents/prompts/system_prompt_v1.md"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout.strip().splitlines()
    assert info["logged"] is False and info["created"] == git[-1]
    moved = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cd",
                            "--date=format:%Y-%m-%d %H:%M:%S", "--", "agents/prompts/system_prompt_v1.md"],
                           cwd=REPO, capture_output=True, text=True, check=True).stdout.strip().splitlines()
    assert info["created"] <= moved[-1]
