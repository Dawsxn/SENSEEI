"""Serve the built frontend from the same service as the API.

One service, one deploy, one origin (docs/context/tech-stack.md). The session
cookie, the OAuth redirect and every fetch in the frontend assume the page and
the API share an origin, so nothing here needs CORS.

Every path the API does not own is the single-page app: a file from `dist/` if
one matches, and otherwise `index.html`, so a refreshed or bookmarked page like
`/classes/abc` loads the app and the app's router takes over.

Paths under an API prefix never fall back to the app. A mistyped API call must
fail as an API call, with a JSON 404, rather than return a page of HTML that a
fetch would then try to parse.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

#: First path segments that belong to the API, not to the app. A page route must
#: never use one of these (the deploy checklist in tech-stack.md says why).
API_PREFIXES = frozenset(
    {
        "auth",
        "enrolments",
        "health",
        "instructor",
        "readings",
        "rubric",
        "sessions",
        "docs",
        "redoc",
        "openapi.json",
    }
)

# pdf.js ships its worker as `.mjs`, and Python's table of file types does not
# always know that extension. Served as anything but JavaScript, the browser
# refuses to start the worker and the PDF viewer never loads.
mimetypes.add_type("text/javascript", ".mjs")


def mount_frontend(app: FastAPI, dist: Path) -> bool:
    """Serve `dist` if it has been built. Returns whether it was mounted.

    Must be called after every API router is included: the catch-all route
    would otherwise shadow them.
    """
    dist = dist.resolve()
    index = dist / "index.html"
    if not index.is_file():
        return False

    assets = dist / "assets"
    if assets.is_dir():
        # Vite names these by content hash, so a changed file is a new name and
        # they can be cached for as long as the browser likes.
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    router = APIRouter(include_in_schema=False)

    @router.get("/{path:path}")
    async def spa(path: str) -> FileResponse:
        if path.split("/", 1)[0] in API_PREFIXES:
            raise HTTPException(status_code=404, detail="not found")
        candidate = (dist / path).resolve()
        # `dist in parents` keeps a crafted `../` from reading outside dist.
        if path and candidate.is_file() and dist in candidate.parents:
            return FileResponse(candidate)
        # The page itself must never be cached: it names the current asset
        # hashes, and a stale copy would point at files a deploy removed.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    app.include_router(router)
    return True
