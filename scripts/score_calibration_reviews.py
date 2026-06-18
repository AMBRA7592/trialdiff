#!/usr/bin/env python3
"""Score blinded TrialDiff v0.2 calibration reviews against the private crosswalk."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


HIGH_PLUS = {"critical", "high"}
ORDER = ["critical", "high", "medium", "low", "insufficient_evidence"]


def load_jsonl(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        review_id = row.get("review_record_id")
        if not review_id:
            raise ValueError(f"{path}: missing review_record_id on line {line_number}")
        if review_id in rows:
            raise ValueError(f"{path}: duplicate review_record_id {review_id}")
        rows[review_id] = row
    return rows


def load_crosswalk(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def ordered_counter(counter: Counter) -> dict[str, int]:
    return {key: counter[key] for key in ORDER if counter[key]}


def score_review(crosswalk: list[dict], review: dict[str, dict]) -> dict:
    joined = []
    missing = []
    for row in crosswalk:
        review_id = row["review_record_id"]
        if review_id not in review:
            missing.append(review_id)
            continue
        joined.append((row, review[review_id]))

    if missing:
        raise ValueError(f"missing review rows: {', '.join(missing[:10])}")

    severity_matrix: dict[str, Counter] = defaultdict(Counter)
    category_matrix: dict[str, Counter] = defaultdict(Counter)
    for row, reviewed in joined:
        assigned = reviewed["assigned_priority"]
        severity_matrix[row["trialdiff_severity"]][assigned] += 1
        if row["trialdiff_severity"] in HIGH_PLUS:
            category_matrix[row["trialdiff_category"]][assigned] += 1

    critical = [(row, reviewed) for row, reviewed in joined if row["trialdiff_severity"] == "critical"]
    high_plus = [(row, reviewed) for row, reviewed in joined if row["trialdiff_severity"] in HIGH_PLUS]

    critical_not_confirmed = sum(1 for _, reviewed in critical if reviewed["assigned_priority"] != "critical")
    high_plus_not_confirmed = sum(
        1 for _, reviewed in high_plus if reviewed["assigned_priority"] not in HIGH_PLUS
    )

    return {
        "review_rows": len(review),
        "review_distribution": ordered_counter(Counter(r["assigned_priority"] for r in review.values())),
        "severity_matrix": {
            severity: ordered_counter(severity_matrix[severity])
            for severity in ["critical", "high", "medium", "low"]
        },
        "critical_not_confirmed": critical_not_confirmed,
        "critical_total": len(critical),
        "critical_not_confirmed_rate": critical_not_confirmed / len(critical),
        "high_plus_not_confirmed": high_plus_not_confirmed,
        "high_plus_total": len(high_plus),
        "high_plus_not_confirmed_rate": high_plus_not_confirmed / len(high_plus),
        "high_plus_by_category": {
            category: ordered_counter(counts)
            for category, counts in sorted(category_matrix.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk", type=Path, default=Path("CALIBRATION_REVIEW_CROSSWALK_PRIVATE_v0.2.csv"))
    parser.add_argument("reviews", nargs="+", type=Path)
    args = parser.parse_args()

    crosswalk = load_crosswalk(args.crosswalk)
    output = {
        "crosswalk_rows": len(crosswalk),
        "reviews": {
            path.name: score_review(crosswalk, load_jsonl(path))
            for path in args.reviews
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
