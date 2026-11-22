"""Local prompt/rubric editor with automatic versioning.

  python serve.py                 # http://127.0.0.1:8765
  python serve.py --port 9000 --no-open

Edits are saved as the next agents/prompts/system_prompt_vN.md or agents/rubrics/rubric_vN.yaml;
existing versions are never overwritten, and nothing is pinned for you. It listens on localhost only.
"""

import argparse
import sys
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
# Run from a checkout without `pip install -e .` too: the agents package sits beside this folder.
if str(BASE.parent) not in sys.path:
    sys.path.insert(1, str(BASE.parent))

from src.webui import make_server  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--base", default=str(BASE), help="the assessment-agent-eval folder; prompts and rubrics are read from ../agents")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = ap.parse_args(argv)
    try:
        server = make_server(Path(args.base), port=args.port)
    except OSError as e:
        print(f"Could not start on port {args.port}: {e}. Try --port with another number.",
              file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Prompt editor running at {url}  (Ctrl+C to stop)")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
