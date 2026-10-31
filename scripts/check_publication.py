"""Reject tracked files that repository ignore rules designate local-only."""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    files = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True).stdout
    if not files:
        return 0
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-z", "--stdin"],
        input=files, capture_output=True,
    )
    if result.returncode not in (0, 1):
        sys.stderr.buffer.write(result.stderr)
        return result.returncode
    blocked = [p.decode("utf-8", "replace") for p in result.stdout.split(b"\0") if p]
    if blocked:
        print("Publication blocked: ignored/local-only files are tracked:", file=sys.stderr)
        for path in blocked:
            print(f"  {path}", file=sys.stderr)
        return 1
    print("Publication paths checked: no ignored/local-only files tracked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
