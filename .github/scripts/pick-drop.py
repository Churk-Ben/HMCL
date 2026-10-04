#!/usr/bin/env python3
"""Chooses which applied pull request to drop after a failed build.

Several upstream pull requests can be individually valid yet conflict
semantically once merged together (for example one refactors an API that
another still uses). ``select-prs.py`` cannot see that, so the compose step
builds the result and, on failure, calls this script to pick the pull request
that most likely caused it.

The script reads the compiler output, extracts the files that produced errors,
and returns the applied pull request whose changed files overlap those the
most. Ties are broken by the lower ranking score. Prints the number, or nothing
when no applied pull request touches the failing files.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ERROR_PATTERN = re.compile(r"(\S+\.java):\d+:\s*error")


def main() -> int:
    pool_path, applied_path, build_log_path, workspace = (Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), str(sys.argv[4]))
    pool = {str(item["number"]): item for item in json.loads(pool_path.read_text(encoding="utf-8")).get("applied_pool", [])}
    applied = applied_path.read_text(encoding="utf-8").split()

    prefix = workspace.rstrip("/") + "/"
    failing: set[str] = set()
    for match in ERROR_PATTERN.finditer(build_log_path.read_text(encoding="utf-8", errors="ignore")):
        path = match.group(1)
        if path.startswith(prefix):
            path = path[len(prefix):]
        failing.add(path)

    if not failing:
        return 0

    best_number = ""
    best_key = (0, 0.0)
    for number in applied:
        item = pool.get(number)
        if not item:
            continue
        overlap = len(set(item.get("files", [])) & failing)
        if overlap == 0:
            continue
        key = (overlap, -float(item.get("score", 0.0)))
        if key > best_key:
            best_key = key
            best_number = number

    if best_number:
        print(best_number)
    return 0


if __name__ == "__main__":
    sys.exit(main())
