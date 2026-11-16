import http.client
import json
import threading
import urllib.error
import urllib.request

import pytest

from src.webui import PAGE, make_server


@pytest.fixture
def server(base, restore_rubric):
    srv = make_server(base, port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def prompts(srv):
    return srv.base.parent / "agents" / "prompts"


def call(srv, path, body=None, headers=None, method=None):
    url = f"http://127.0.0.1:{srv.server_port}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    h = {"Content-Type": "application/json", **(headers or {})} if body is not None else dict(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if "json" in r.headers.get("Content-Type", "") else raw.decode())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw.decode()


def test_it_only_listens_on_localhost(server):
    assert server.server_address[0] == "127.0.0.1"


def test_serves_the_editor_page(server):
    status, html = call(server, "/")
    assert status == 200 and "<textarea" in html


def test_state_lists_versions_next_number_and_pins(server):
    status, state = call(server, "/api/state")
    assert status == 200
    assert state["prompt"]["versions"] == [3] and state["prompt"]["next"] == 4
    assert state["rubric"]["pinned"]["3"] == ["config.yaml"]


def test_text_endpoint_returns_a_version_and_rejects_bad_input(server):
    status, body = call(server, "/api/text?kind=prompt&n=3")
    assert status == 200 and "{{RUBRIC}}" in body["text"]
    assert call(server, "/api/text?kind=prompt&n=99")[0] == 400
    assert call(server, "/api/text?kind=prompt&n=../../config")[0] == 400
    assert call(server, "/api/text?kind=secrets&n=1")[0] == 400


def test_check_reports_errors_warnings_and_diff_without_writing(server):
    _, base = call(server, "/api/text?kind=prompt&n=3")
    status, res = call(server, "/api/check", {"kind": "prompt", "based_on": 3,
                                              "text": base["text"].replace("Be strict but fair.", "Be fair.")})
    assert status == 200 and res["changed"] and res["errors"] == []
    assert any(l.startswith("+") and "Be fair." in l for l in res["diff"])
    status, res = call(server, "/api/check", {"kind": "prompt", "based_on": 3, "text": "no slot here"})
    assert res["errors"]
    assert not (prompts(server) / "system_prompt_v4.md").exists()


def test_save_writes_the_next_version_into_agents_and_returns_the_run_command(server):
    _, base = call(server, "/api/text?kind=prompt&n=3")
    status, res = call(server, "/api/save", {"kind": "prompt", "based_on": 3, "note": "tighten",
                                             "text": base["text"].replace("Be strict but fair.", "Be fair.")})
    assert status == 200 and res["version"] == 4
    assert res["path"] == "agents/prompts/system_prompt_v4.md"
    assert res["command"] == "python run_eval.py --prompt ../agents/prompts/system_prompt_v4.md"
    assert (prompts(server) / "system_prompt_v4.md").exists()
    _, state = call(server, "/api/state")
    assert state["prompt"]["versions"] == [3, 4] and state["prompt"]["next"] == 5


def test_saving_a_rubric_returns_its_run_command(server):
    _, base = call(server, "/api/text?kind=rubric&n=3")
    status, res = call(server, "/api/save", {"kind": "rubric", "based_on": 3,
                                             "text": base["text"].replace("not vague.", "not vague at all.")})
    assert status == 200 and res["path"] == "agents/rubrics/rubric_v4.yaml"
    assert res["command"] == "python run_eval.py --rubric ../agents/rubrics/rubric_v4.yaml"


def test_saving_without_changes_or_with_errors_writes_nothing(server):
    _, base = call(server, "/api/text?kind=prompt&n=3")
    status, res = call(server, "/api/save", {"kind": "prompt", "based_on": 3, "text": base["text"]})
    assert status == 400 and "no changes" in res["error"]
    status, res = call(server, "/api/save", {"kind": "prompt", "based_on": 3, "text": "x"})
    assert status == 400 and "{{RUBRIC}}" in res["error"]
    assert call(server, "/api/state")[1]["prompt"]["versions"] == [3]


def test_preview_returns_the_composed_prompt_and_hash(server):
    _, base = call(server, "/api/text?kind=prompt&n=3")
    status, res = call(server, "/api/preview", {"text": base["text"], "rubric": 3})
    assert status == 200 and "{{RUBRIC}}" not in res["text"] and "### STATE" in res["text"]
    assert len(res["hash"]) == 10


def test_a_page_on_another_host_cannot_drive_it(server):
    port = server.server_port
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", "/api/state", headers={"Host": "evil.example.com"})
    assert conn.getresponse().status == 403
    body = json.dumps({"kind": "prompt", "based_on": 3, "text": "x"})
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("POST", "/api/save", body, headers={"Content-Type": "application/json",
                                                     "Origin": "http://evil.example.com"})
    assert conn.getresponse().status == 403


def test_posts_must_be_json(server):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
    conn.request("POST", "/api/save", "kind=prompt", headers={"Content-Type": "text/plain"})
    assert conn.getresponse().status == 415


def test_unknown_paths_404_and_malformed_json_400(server):
    assert call(server, "/nope")[0] == 404
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
    conn.request("POST", "/api/check", "{not json", headers={"Content-Type": "application/json"})
    assert conn.getresponse().status == 400


def save_v4(server):
    _, base = call(server, "/api/text?kind=prompt&n=3")
    call(server, "/api/save", {"kind": "prompt", "based_on": 3, "note": "loosen",
                               "text": base["text"].replace("Be strict but fair.", "Be fair.")})


def test_compare_returns_the_diff_both_versions_info_and_logged_runs(server):
    save_v4(server)
    (server.base / "results_log.csv").write_text(
        "timestamp,prompt_version,rubric_version,example_set_version,model,total,verdict_accuracy,report_file\n"
        "20261101_100000,v3,v3,v3,gemini-3.1-pro-preview,71,0.883,r1.html\n", encoding="utf-8")
    status, res = call(server, "/api/compare?kind=prompt&a=3&b=4")
    assert status == 200 and res["changed"] and (res["added"], res["removed"]) == (1, 1)
    assert any(l.startswith("+") and "Be fair." in l for l in res["diff"])
    assert res["a"]["info"]["logged"] is False and res["b"]["info"]["note"] == "loosen"
    assert [r["report_file"] for r in res["a"]["runs"]] == ["r1.html"] and res["b"]["runs"] == []
    assert res["a"]["runs"][0]["total"] == "71"
    whole = call(server, "/api/compare?kind=prompt&a=3&b=4&context=all")[1]
    assert len(whole["diff"]) > len(res["diff"])


def test_compare_rejects_bad_input(server):
    assert call(server, "/api/compare?kind=prompt&a=3&b=99")[0] == 400
    assert call(server, "/api/compare?kind=prompt&a=x&b=3")[0] == 400
    assert call(server, "/api/compare?kind=secrets&a=3&b=3")[0] == 400
    assert call(server, "/api/compare?kind=prompt&a=3&b=3&context=-1")[0] == 400


def test_the_page_shows_the_columns_this_log_has():
    html = PAGE.read_text(encoding="utf-8")
    for col in ("verdict_accuracy", "criteria_exact_rate", "example_set_version", "r.total"):
        assert col in html
    assert "overall_agreement" not in html and "r.split" not in html
