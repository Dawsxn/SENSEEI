"""Start the app as a deploy does: migrate, seed if asked, then serve.

    python scripts/start.py

This is the container's command. Migrations run here, on every start, rather
than as a separate deploy step: the free hosting tier has no pre-deploy hook,
and running them on start means development rehearses exactly what production
will do (docs/context/tech-stack.md).

A Python script rather than a shell one so it runs the same from a Windows
checkout, where a shell script's line endings can quietly break it in Linux.

Environment:

    PORT            where to listen; the host sets it (default 8000)
    SEED_IF_EMPTY   "true" to fill an empty database with the development seed.
                    For the development environment only, never production: it
                    is what makes a fresh database usable at all, and it does
                    nothing once the database has users in it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args: str) -> None:
    print("$", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    run(sys.executable, "-m", "alembic", "upgrade", "head")

    if os.environ.get("SEED_IF_EMPTY", "").lower() == "true":
        run(sys.executable, "scripts/seed.py", "--if-empty", "--force")

    port = os.environ.get("PORT", "8000")
    # Replace this process with the server, so the host's stop signal reaches
    # uvicorn directly. --proxy-headers because the host terminates HTTPS in
    # front of us: without it the app believes every request is plain http.
    os.chdir(ROOT)
    os.execvp(
        sys.executable,
        [
            sys.executable, "-m", "uvicorn", "backend.main:app",
            "--host", "0.0.0.0",
            "--port", port,
            "--proxy-headers",
            "--forwarded-allow-ips", "*",
        ],
    )


if __name__ == "__main__":
    main()
