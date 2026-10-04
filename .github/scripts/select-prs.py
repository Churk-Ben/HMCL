#!/usr/bin/env python3
"""Multi-dimensional pull-request selector for the HMCL experimental channel.

This script queries the open pull requests of an upstream repository, applies
hard filters, scores every remaining candidate across a set of configurable
dimensions, and emits the selected pull-request numbers for aggregation.

The scoring model is intentionally pluggable: each dimension declares a metric
and a weight, and the weighted sum of min-max normalised metric values becomes
the candidate score. Dimensions can be added or re-weighted without touching the
selection logic, which keeps the door open for richer multi-dimensional
selection later.

Example:
    python3 .github/scripts/select-prs.py \
        --policy .github/experimental/pr-policy.json \
        --dry-run
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
from typing import Any, Callable

# GraphQL query that returns every open pull request together with the fields
# used by the built-in metrics. Reactions and review decisions are only exposed
# through GraphQL, so a single paginated query is cheaper than per-PR REST calls.
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

# Size labels assigned by .github/scripts/pr-size-label.js, from smallest to
# largest. The index is used as the normalised "size_label" metric.
SIZE_LABELS = ["1+", "10+", "40+", "100+", "500+", "1000+", "2000+", "5000+"]


def run_gh(args: list[str], attempts: int = 3) -> str:
    """Runs the GitHub CLI and returns stdout, retrying transient failures."""
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
        args = [
            "api",
            "graphql",
            "-f",
            f"query={GRAPHQL_QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
        ]
        if cursor:
            args += ["-F", f"cursor={cursor}"]
        payload = json.loads(run_gh(args))
        data = payload["data"]["repository"]["pullRequests"]
        pull_requests.extend(data["nodes"])
        if not data["pageInfo"]["hasNextPage"] or len(pull_requests) >= limit:
            break
        cursor = data["pageInfo"]["endCursor"]
    return pull_requests[:limit]


def thumbs_up(pr: dict[str, Any]) -> float:
    """Returns the number of thumbs-up reactions on the pull request."""
    return float(
        sum(
            group["users"]["totalCount"]
            for group in pr.get("reactionGroups") or []
            if group.get("content") == "THUMBS_UP"
        )
    )


def label_names(pr: dict[str, Any]) -> set[str]:
    """Returns the set of label names attached to the pull request."""
    return {node["name"] for node in (pr.get("labels") or {}).get("nodes", [])}


def age_days(timestamp: str) -> float:
    """Returns the age of an ISO-8601 timestamp in days."""
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0)


# Built-in metric functions. Each maps a pull request to a raw numeric value.
METRICS: dict[str, Callable[[dict[str, Any]], float]] = {
    "thumbs_up": thumbs_up,
    "comments": lambda pr: float((pr.get("comments") or {}).get("totalCount", 0)),
    "changed_lines": lambda pr: float(pr.get("additions", 0) + pr.get("deletions", 0)),
    "changed_files": lambda pr: float(pr.get("changedFiles", 0)),
    "approved": lambda pr: 1.0 if pr.get("reviewDecision") == "APPROVED" else 0.0,
    # Fresher pull requests are more likely to apply cleanly and reflect the
    # current upstream direction; the half-life is roughly one week.
    "recent_update": lambda pr: math.exp(-age_days(pr["updatedAt"]) / 7.0),
    "recent_create": lambda pr: math.exp(-age_days(pr["createdAt"]) / 7.0),
    "size_label": lambda pr: float(
        next((i for i, label in enumerate(SIZE_LABELS) if label in label_names(pr)), 0)
    ),
}


def normalise(values: list[float]) -> list[float]:
    """Min-max normalises a list of values into [0, 1]."""
    if not values:
        return []
    low, high = min(values), max(values)
    if high - low < 1e-12:
        return [0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def passes_filters(pr: dict[str, Any], filters: dict[str, Any]) -> str | None:
    """Returns a rejection reason, or None when the pull request passes."""
    if filters.get("exclude_drafts", True) and pr.get("isDraft"):
        return "draft"
    excluded_labels = label_names(pr) & set(filters.get("exclude_labels") or [])
    if excluded_labels:
        return f"label {sorted(excluded_labels)[0]}"
    if filters.get("require_mergeable", True) and pr.get("mergeable") != "MERGEABLE":
        return f"mergeable={pr.get('mergeable')}"
    return None


def score_candidates(
    candidates: list[dict[str, Any]], dimensions: list[dict[str, Any]]
) -> dict[int, float]:
    """Computes the weighted score of every candidate."""
    # Precompute each dimension's normalised values across all candidates.
    normalised: dict[str, list[float]] = {}
    for dimension in dimensions:
        metric = dimension["metric"]
        if metric not in METRICS:
            raise SystemExit(f"unknown metric: {metric}")
        normalised[dimension["name"]] = normalise([METRICS[metric](pr) for pr in candidates])

    scores: dict[int, float] = {}
    for index, pr in enumerate(candidates):
        scores[pr["number"]] = sum(
            float(dimensions[j].get("weight", 1.0)) * normalised[dimensions[j]["name"]][index]
            for j in range(len(dimensions))
        )
    return scores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path, help="Path to the JSON policy file")
    parser.add_argument("--repo", default="HMCL-dev/HMCL", help="owner/name of the upstream repository")
    parser.add_argument("--top-n", type=int, help="Override the policy top_n")
    parser.add_argument("--include", default="", help="Comma-separated PR numbers to force include")
    parser.add_argument("--exclude", default="", help="Comma-separated PR numbers to force exclude")
    parser.add_argument("--limit", type=int, default=300, help="Maximum open PRs to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Print a report without changing anything")
    parser.add_argument("--github-output", type=Path, help="Append selected numbers to this GITHUB_OUTPUT file")
    parser.add_argument("--report", type=Path, help="Write a Markdown report to this path")
    args = parser.parse_args()

    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    owner, _, name = args.repo.partition("/")
    top_n = args.top_n or int(policy.get("top_n", 5))

    forced_include = {int(x) for x in (args.include or ",".join(map(str, policy.get("include", [])))).split(",") if x.strip()}
    forced_exclude = {int(x) for x in (args.exclude or ",".join(map(str, policy.get("exclude", [])))).split(",") if x.strip()}

    all_prs = fetch_open_prs(owner, name, args.limit)
    by_number = {pr["number"]: pr for pr in all_prs}

    rejected: list[tuple[int, str]] = []
    candidates: list[dict[str, Any]] = []
    for pr in all_prs:
        number = pr["number"]
        if number in forced_exclude:
            rejected.append((number, "excluded by policy"))
            continue
        if number in forced_include:
            candidates.append(pr)
            continue
        reason = passes_filters(pr, policy.get("filters") or {})
        if reason:
            rejected.append((number, reason))
        else:
            candidates.append(pr)

    scores = score_candidates(candidates, policy.get("dimensions") or [])
    ranked = sorted(candidates, key=lambda pr: (-scores[pr["number"]], -pr["number"]))

    # Forced includes always make the cut; the remainder is filled by score.
    selected: list[dict[str, Any]] = [pr for pr in ranked if pr["number"] in forced_include]
    for pr in ranked:
        if len(selected) >= top_n:
            break
        if pr["number"] not in forced_include:
            selected.append(pr)
    selected = sorted(selected, key=lambda pr: -scores.get(pr["number"], 0.0))
    selected_numbers = [pr["number"] for pr in selected]

    lines = ["# Experimental PR selection", ""]
    if selected:
        lines += ["## Selected", "", "| PR | Score | Title |", "| --- | --- | --- |"]
        for pr in selected:
            marker = " (forced)" if pr["number"] in forced_include else ""
            lines.append(f"| [#{pr['number']}]({pr['url']}) | {scores.get(pr['number'], 0.0):.3f}{marker} | {pr['title']} |")
    else:
        lines.append("No pull request selected.")
    if rejected:
        lines += ["", "## Rejected", ""]
        lines += [f"- #{number}: {reason}" for number, reason in rejected[:50]]
    report = "\n".join(lines) + "\n"

    if args.report:
        args.report.write_text(report, encoding="utf-8")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"prs={','.join(map(str, selected_numbers))}\n")
            output.write(f"count={len(selected_numbers)}\n")

    print(report)
    if args.dry_run:
        print(f"dry-run: would select {selected_numbers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
