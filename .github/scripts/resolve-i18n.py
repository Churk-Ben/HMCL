#!/usr/bin/env python3
"""Best-effort three-way merge for conflicted HMCL translation files.

Many upstream pull requests add keys to the same ``I18N*.properties`` files
that the fork's channel layer also touches, so merges conflict even though the
changes are additive. This resolver performs a key-level three-way merge:

* a key changed by only one side is taken from that side;
* a key added by only one side is kept;
* a key changed on both sides keeps ``ours`` and is reported as unresolved.

Only files whose name starts with ``I18N`` and ends with ``.properties`` are
touched. The script exits non-zero when any conflict remains.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

KEY_PATTERN = re.compile(r"\s*([^=:\s]+)\s*[=:]")


def git(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def conflicted_files() -> list[str]:
    result = git("diff", "--name-only", "--diff-filter=U")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def show_stage(stage: int, path: str) -> str | None:
    result = git("show", f":{stage}:{path}")
    return result.stdout if result.returncode == 0 else None


def split_key(line: str) -> str:
    match = KEY_PATTERN.match(line)
    return match.group(1) if match else line.strip()


def parse_blocks(text: str | None) -> tuple[list[str], list[tuple[str, str]]]:
    """Splits a properties file into a leading header and keyed entries."""
    if text is None:
        return [], []
    lines = text.splitlines(keepends=True)
    header: list[str] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].lstrip()
        if stripped.startswith("#") or stripped.startswith("!") or stripped.strip() == "":
            header.append(lines[index])
            index += 1
        else:
            break

    entries: list[tuple[str, str]] = []
    while index < len(lines):
        current = lines[index]
        stripped = current.lstrip()
        if stripped.startswith("#") or stripped.startswith("!") or stripped.strip() == "":
            index += 1
            continue
        block = [current]
        while current.rstrip("\n").endswith("\\") and index + 1 < len(lines):
            index += 1
            current = lines[index]
            block.append(current)
        entries.append((split_key(block[0]), "".join(block)))
        index += 1
    return header, entries


def merge(base: list[tuple[str, str]], ours: list[tuple[str, str]], theirs: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    order: list[str] = []
    seen: set[str] = set()
    for key, _ in ours + theirs:
        if key not in seen:
            seen.add(key)
            order.append(key)

    base_map = dict(base)
    ours_map = dict(ours)
    theirs_map = dict(theirs)

    merged: list[str] = []
    unresolved: list[str] = []
    for key in order:
        our_value = ours_map.get(key)
        their_value = theirs_map.get(key)
        base_value = base_map.get(key)
        if our_value == their_value:
            chosen = our_value
        elif our_value == base_value:
            chosen = their_value
        elif their_value == base_value:
            chosen = our_value
        else:
            chosen = our_value
            unresolved.append(key)
        if chosen is not None:
            merged.append(chosen)
    return merged, unresolved


def resolve(path: str) -> bool:
    base_header, base = parse_blocks(show_stage(1, path))
    our_header, ours = parse_blocks(show_stage(2, path))
    _, theirs = parse_blocks(show_stage(3, path))

    merged, unresolved = merge(base, ours, theirs)
    header = our_header or base_header
    Path(path).write_text("".join(header) + "".join(merged), encoding="utf-8")
    git("add", "--", path)
    if unresolved:
        print(f"{path}: kept 'ours' for {len(unresolved)} key(s): {', '.join(sorted(unresolved)[:5])}")
    else:
        print(f"{path}: merged")
    return not unresolved


def main() -> int:
    targets = [f for f in conflicted_files() if Path(f).name.startswith("I18N") and f.endswith(".properties")]
    if not targets:
        return 1

    ok = True
    for path in targets:
        try:
            ok = resolve(path) and ok
        except Exception as exc:  # noqa: BLE001 - report and leave the conflict in place
            print(f"{path}: resolver failed: {exc}")
            ok = False

    remaining = conflicted_files()
    if remaining:
        print("still conflicted: " + ", ".join(remaining))
        return 1
    return 0 if ok else 0


if __name__ == "__main__":
    sys.exit(main())
