#!/usr/bin/env python3
"""Manual smoke: POST /generate against a running backend.

Usage:
  python scripts/legacy/smoke_generate.py [--base http://127.0.0.1:8000] [--model qwen2.5:0.5b]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test /generate")
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="qwen2.5:0.5b")
    parser.add_argument(
        "--prompt",
        default="Write a short prompt for summarizing meeting notes",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Client timeout in seconds; iterative refinement of small local "
        "models on CPU can exceed the default",
    )
    args = parser.parse_args()

    payload = {
        "user_input": args.prompt,
        "profile_key": "technical",
        "model": args.model,
    }
    req = urllib.request.Request(
        f"{args.base.rstrip('/')}/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print("HTTP", resp.status)
            print(json.dumps(body, indent=2)[:2000])
            return 0 if body.get("success", True) else 2
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, exc.read().decode("utf-8", errors="replace")[:500])
        return 1
    except Exception as exc:
        print("ERROR", type(exc).__name__, exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
