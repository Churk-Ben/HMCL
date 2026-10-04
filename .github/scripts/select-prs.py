#!/usr/bin/env python3
"""Purpose-driven pull-request ranking for the HMCL experimental channel.

The experimental channel exists to let users try impactful upstream changes
early. A candidate is therefore ranked by::

    score = value x feasibility

* ``value`` favours interesting/impactful, likely-to-land changes
  (category labels, review momentum, popularity, change size).
* ``feasibility`` estimates how likely the pull request is to merge cleanly
  (mergeability, overlap with the fork's own layers, staleness). It is a
  multiplier, so a high-value pull request that will certainly conflict is
  ranked below a slightly less valuable one that will apply.

The script emits a *ranked pool* rather than a fixed count, so the compose step
can try candidates in order and stop once it has applied enough.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# GraphQL query returning every open pull request with the ranking fields.
# Changed files are fetched separately (REST) to keep this query cheap.
GRAPHQL_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 100, states: OPEN, after: $cursor, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        url
        isDraft
        additions
        deletions
        changedFiles
        createdAt
        updatedAt
        mergeable
        mergeStateStatus
        reviewDecision
        labels(first: 50) { nodes { name } }
        reactionGroups { content users { totalCount } }
        comments { totalCount }
      }
    }
  }
}
"""


def run_gh(args: list[str], attempts: int = 3) -> str:
    """Runs the GitHub CLI, retrying transient failures."""
    last_error = ""
    for attempt in range(1, attempts + 1):
        result = subprocess.run(["gh", *args], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        last_error = result.stderr.strip()
        if attempt < attempts:
            time.sleep(2 * attempt)
    raise RuntimeError(f"gh {args[0]} failed after {attempts} attempts: {last_error}")


def fetch_open_prs(owner: str, name: str, limit: int) -> list[dict[str, Any]]:
    """Fetches open pull requests through the GitHub GraphQL API."""
    pull_requests: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        args = ["api", "graphql", "-f", f"query={GRAPHQL_QUERY}", "-F", f"owner={owner}", "-F", f"name={name}"]
        if cursor:
            args += ["-F", f"cursor={cursor}"]
        data = json.loads(run_gh(args))["data"]["repository"]["pullRequests"]
        pull_requests.extend(data["nodes"])
        if not data["pageInfo"]["hasNextPage"] or len(pull_requests) >= limit:
            break
        cursor = data["pageInfo"]["endCursor"]
    return pull_requests[:limit]


def fetch_changed_files(repo: str, number: int) -> set[str]:
    """Returns the set of files changed by a pull request (REST)."""
    try:
        output = run_gh(["api", f"repos/{repo}/pulls/{number}/files?per_page=100", "--jq", ".[].filename"])
    except RuntimeError:
        return set()
    return {line.strip() for line in output.splitlines() if line.strip()}


def thumbs_up(pr: dict[str, Any]) -> float:
    return float(
        sum(
            group["users"]["totalCount"]
            for group in pr.get("reactionGroups") or []
            if group.get("content") == "THUMBS_UP"
        )
    )


def label_names(pr: dict[str, Any]) -> set[str]:
    return {node["name"] for node in (pr.get("labels") or {}).get("nodes", [])}


def age_days(timestamp: str) -> float:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def min_max(values: list[float]) -> list[float]:
    """Min-max normalises values into [0, 1]; constant inputs become 0.5."""
    if not values:
        return []
    low, high = min(values), max(values)
    if high - low < 1e-12:
        return [0.5 for _ in values]
    return [(value - low) / (high - low) for value in values]


def passes_filters(pr: dict[str, Any], filters: dict[str, Any]) -> str | None:
    if filters.get("exclude_drafts", True) and pr.get("isDraft"):
        return "draft"
    excluded = label_names(pr) & set(filters.get("exclude_labels") or [])
    if excluded:
        return f"label {sorted(excluded)[0]}"
    if filters.get("require_mergeable", True) and pr.get("mergeable") != "MERGEABLE":
        return f"mergeable={pr.get('mergeable')}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--repo", default="HMCL-dev/HMCL")
    parser.add_argument("--target", type=int, help="Override the intended number of applied pull requests")
    parser.add_argument("--pool-size", type=int, help="Override the ranked pool size")
    parser.add_argument("--include", default="")
    parser.add_argument("--exclude", default="")
    parser.add_argument("--conflict-files", type=Path, help="File with one path per line that the fork's layers change")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--report-json", type=Path, help="Machine-readable pool metadata for release notes")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    owner, _, name = args.repo.partition("/")
    target = args.target or int(policy.get("target", 20))
    pool_size = args.pool_size or int(policy.get("pool_size", max(target * 3, target + 30)))

    include = {int(x) for x in (args.include or ",".join(map(str, policy.get("include", [])))).split(",") if x.strip()}
    exclude = {int(x) for x in (args.exclude or ",".join(map(str, policy.get("exclude", [])))).split(",") if x.strip()}

    conflict_files: set[str] = set()
    if args.conflict_files and args.conflict_files.is_file():
        conflict_files = {line.strip() for line in args.conflict_files.read_text().splitlines() if line.strip()}

    all_prs = fetch_open_prs(owner, name, args.limit)
    filters = policy.get("filters") or {}
    weights = policy.get("weights") or {}
    category_scores = policy.get("category_scores") or {}
    category_default = float(policy.get("category_default", 0.3))
    feasibility_cfg = policy.get("feasibility") or {}
    overlap_penalty = float(feasibility_cfg.get("overlap_penalty", 1.2))
    staleness_penalty = float(feasibility_cfg.get("staleness_penalty", 0.5))
    staleness_days = float(feasibility_cfg.get("staleness_days", 30))
    feasibility_floor = float(feasibility_cfg.get("floor", 0.05))

    rejected: list[tuple[int, str]] = []
    candidates: list[dict[str, Any]] = []
    for pr in all_prs:
        number = pr["number"]
        pr["_files"] = fetch_changed_files(args.repo, number)
        if number in exclude:
            rejected.append((number, "excluded by policy"))
            continue
        if number in include:
            candidates.append(pr)
            continue
        reason = passes_filters(pr, filters)
        if reason:
            rejected.append((number, reason))
        else:
            candidates.append(pr)

    momentum_raw = [0.7 * (1.0 if pr.get("reviewDecision") == "APPROVED" else 0.0) + 0.3 * math.exp(-age_days(pr["updatedAt"]) / 14.0) for pr in candidates]
    popularity_raw = [math.log1p(thumbs_up(pr)) for pr in candidates]
    impact_raw = [math.log1p(pr.get("additions", 0) + pr.get("deletions", 0)) for pr in candidates]
    momentum = min_max(momentum_raw)
    popularity = min_max(popularity_raw)
    impact = min_max(impact_raw)

    scored: list[dict[str, Any]] = []
    for i, pr in enumerate(candidates):
        labels = label_names(pr)
        category = max((float(category_scores.get(label, category_default)) for label in labels), default=category_default)
        files = pr["_files"]
        overlap = len(files & conflict_files) / len(files) if files and conflict_files else 0.0
        staleness = clamp(age_days(pr["updatedAt"]) / staleness_days, 0.0, 1.0)
        feasibility = clamp(1.0 - overlap_penalty * overlap - staleness_penalty * staleness, feasibility_floor, 1.0)
        value = (
            float(weights.get("category", 1.0)) * category
            + float(weights.get("momentum", 0.8)) * momentum[i]
            + float(weights.get("popularity", 0.5)) * popularity[i]
            + float(weights.get("impact", 1.0)) * impact[i]
        )
        pr["_score"] = value * feasibility
        pr["_message"] = f"value={value:.3f} feasibility={feasibility:.3f} overlap={overlap:.2f}"
        scored.append(pr)

    scored.sort(key=lambda pr: (-pr["_score"], -pr["number"]))
    includes = [pr for pr in scored if pr["number"] in include]
    rest = [pr for pr in scored if pr["number"] not in include]
    pool = (includes + rest)[:pool_size]

    lines = [f"# Experimental PR pool (target {target}, pool {pool_size})", "", "| PR | Score | Labels | Value signals |", "| --- | --- | --- | --- |"]
    for pr in pool:
        labels = ",".join(sorted(label_names(pr)))
        lines.append(f"| [#{pr['number']}]({pr['url']}) | {pr['_score']:.3f} | {labels or '-'} | {pr['_message']} |")
    if rejected:
        lines += ["", "## Rejected", ""]
        lines += [f"- #{number}: {reason}" for number, reason in rejected[:80]]
    report = "\n".join(lines) + "\n"

    if args.report:
        args.report.write_text(report, encoding="utf-8")
    if args.report_json:
        payload = {
            "target": target,
            "pool_size": pool_size,
            "applied_pool": [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "url": pr["url"],
                    "labels": sorted(label_names(pr)),
                    "score": round(pr["_score"], 4),
                }
                for pr in pool
            ],
        }
        args.report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"prs={','.join(str(pr['number']) for pr in pool)}\n")
            output.write(f"count={len(pool)}\n")

    print(report)
    if args.dry_run:
        print("dry-run pool:", [pr["number"] for pr in pool])
    return 0


if __name__ == "__main__":
    sys.exit(main())
