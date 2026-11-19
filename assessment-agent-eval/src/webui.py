"""The local prompt/rubric editor: a small JSON API plus one page (``ui/editor.html``).

Standard library only, bound to 127.0.0.1. It writes only through ``versions.save_version``, so it
can add a new version but never overwrite one. Because it can write files, it also refuses requests
whose Host or Origin is not this server, and POSTs that are not JSON, so a web page you happen to
have open cannot drive it.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import versions
from .versions import VersionError

PAGE = Path(__file__).resolve().parent.parent / "ui" / "editor.html"
MAX_BODY = 1_000_000


def _repo_path(base: Path, path: Path) -> str:
    """``path`` relative to the repository root (the folder holding ``agents/``), with / slashes."""
    try:
        return path.resolve().relative_to(Path(base).resolve().parent).as_posix()
    except ValueError:
        return path.as_posix()


def _int(value, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise VersionError(f"{name} must be a whole number, got {value!r}") from None


class Handler(BaseHTTPRequestHandler):
    server: "EditorServer"

    def log_message(self, *args) -> None:   # keep the terminal quiet
        pass

    # ---- plumbing
    def _send(self, status: int, payload, content_type: str = "application/json") -> None:
        body = (payload if isinstance(payload, str) else json.dumps(payload)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._send(status, {"error": message})

    def _allowed_hosts(self) -> set[str]:
        port = self.server.server_port
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _local_only(self) -> bool:
        if self.headers.get("Host") not in self._allowed_hosts():
            self._error(403, "this editor only answers to localhost")
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{h}" for h in self._allowed_hosts()}:
            self._error(403, "request came from another origin")
            return False
        return True

    # ---- routes
    def do_GET(self) -> None:
        if not self._local_only():
            return
        url = urlparse(self.path)
        query = parse_qs(url.query)
        try:
            if url.path == "/":
                self._send(200, PAGE.read_text(encoding="utf-8"), "text/html")
            elif url.path == "/api/state":
                self._send(200, self._state())
            elif url.path == "/api/compare":
                self._send(200, self._compare(query))
            elif url.path == "/api/text":
                kind = query.get("kind", [""])[0]
                n = _int(query.get("n", [""])[0], "n")
                self._send(200, {"text": versions.read_version(self.server.base, kind, n)})
            else:
                self._error(404, "not found")
        except VersionError as e:
            self._error(400, str(e))

    def do_POST(self) -> None:
        if not self._local_only():
            return
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            self._error(415, "send JSON")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._error(413, "too large")
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            self._error(400, "body must be a JSON object")
            return
        base = self.server.base
        try:
            path = urlparse(self.path).path
            if path == "/api/check":
                res = versions.check(base, str(body.get("kind")), str(body.get("text", "")),
                                     _int(body.get("based_on"), "based_on"))
                self._send(200, {"errors": res.errors, "warnings": res.warnings,
                                 "diff": res.diff, "changed": res.changed})
            elif path == "/api/save":
                kind = str(body.get("kind"))
                n = versions.save_version(base, kind, str(body.get("text", "")),
                                          _int(body.get("based_on"), "based_on"),
                                          str(body.get("note", "")))
                self._send(200, {"version": n, "path": _repo_path(base, versions.path_for(base, kind, n)),
                                 "command": self._command(kind, n)})
            elif path == "/api/preview":
                text, digest = versions.preview(base, str(body.get("text", "")),
                                                _int(body.get("rubric"), "rubric"))
                self._send(200, {"text": text, "hash": digest})
            else:
                self._error(404, "not found")
        except VersionError as e:
            self._error(400, str(e))

    # ---- content
    def _compare(self, query: dict) -> dict:
        base = self.server.base
        kind = query.get("kind", [""])[0]
        a, b = _int(query.get("a", [""])[0], "a"), _int(query.get("b", [""])[0], "b")
        raw = query.get("context", ["3"])[0]
        result = versions.compare(base, kind, a, b, None if raw == "all" else _int(raw, "context"))
        return {"diff": result.diff, "added": result.added, "removed": result.removed,
                "changed": result.changed,
                "a": {"info": versions.version_info(base, kind, a), "runs": versions.runs_for(base, kind, a)},
                "b": {"info": versions.version_info(base, kind, b), "runs": versions.runs_for(base, kind, b)}}

    def _state(self) -> dict:
        base, pins = self.server.base, versions.pinned(self.server.base)
        return {kind: {"versions": versions.list_versions(base, kind),
                       "next": versions.next_version(base, kind),
                       "pinned": {str(n): files for n, files in pins[kind].items()}}
                for kind in ("prompt", "rubric")}

    @staticmethod
    def _command(kind: str, n: int) -> str:
        flag, path = {"prompt": ("--prompt", f"../agents/prompts/system_prompt_v{n}.md"),
                      "rubric": ("--rubric", f"../agents/rubrics/rubric_v{n}.yaml")}[kind]
        return f"python run_eval.py {flag} {path}"


class EditorServer(HTTPServer):
    base: Path


def make_server(base: Path, host: str = "127.0.0.1", port: int = 8765) -> EditorServer:
    server = EditorServer((host, port), Handler)
    server.base = Path(base)
    return server
