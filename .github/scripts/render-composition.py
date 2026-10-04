#!/usr/bin/env python3
"""Renders the release-note section describing one experimental composition.

Reads the machine-readable pool produced by ``select-prs.py`` plus the applied
and skipped pull-request numbers, and writes a Markdown section that lists the
upstream pull requests included in the release with their titles and links.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    pool_path, applied_path, skipped_path, output_path = (Path(arg) for arg in sys.argv[1:5])
    pool = {str(item["number"]): item for item in json.loads(pool_path.read_text(encoding="utf-8")).get("applied_pool", [])}
    applied = applied_path.read_text(encoding="utf-8").split()
    skipped = skipped_path.read_text(encoding="utf-8").split()

    def render(numbers: list[str]) -> str:
        lines = []
        for number in numbers:
            item = pool.get(number)
            if item:
                lines.append(f"- [#{number}]({item['url']}) {item['title']}")
            else:
                lines.append(f"- #{number}")
        return "\n".join(lines) if lines else "- (none)"

    output_path.write_text(
        "## Aggregated upstream pull requests\n\n"
        f"### Included ({len(applied)})\n{render(applied)}\n\n"
        f"### Skipped on conflict ({len(skipped)})\n{render(skipped)}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
