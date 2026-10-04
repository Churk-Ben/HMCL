#!/usr/bin/env python3
"""Renders the release-note section describing one experimental composition.

Reads the machine-readable pool produced by ``select-prs.py`` plus the applied,
conflict-skipped and build-dropped pull-request numbers, and writes a Markdown
section listing the upstream pull requests with their titles and links.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    pool_path, applied_path, skipped_path, dropped_path, output_path = (Path(arg) for arg in sys.argv[1:6])
    pool = {str(item["number"]): item for item in json.loads(pool_path.read_text(encoding="utf-8")).get("applied_pool", [])}

    def read(path: Path) -> list[str]:
        return path.read_text(encoding="utf-8").split() if path.is_file() else []

    applied = read(applied_path)
    skipped = read(skipped_path)
    dropped = read(dropped_path)

    def render(numbers: list[str]) -> str:
        lines = []
        for number in numbers:
            item = pool.get(number)
            lines.append(f"- [#{number}]({item['url']}) {item['title']}" if item else f"- #{number}")
        return "\n".join(lines) if lines else "- (none)"

    output_path.write_text(
        "## Aggregated upstream pull requests\n\n"
        f"### Included ({len(applied)})\n{render(applied)}\n\n"
        f"### Skipped on conflict ({len(skipped)})\n{render(skipped)}\n\n"
        f"### Dropped after build failure ({len(dropped)})\n{render(dropped)}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
