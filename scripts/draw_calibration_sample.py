from __future__ import annotations

import argparse
import csv
import hashlib
import sqlite3
from pathlib import Path


DEFAULT_SEED = "trialdiff-v0.2-calibration-a764e33"
TARGETS = {
    "critical": 30,
    "high": 30,
    "medium": 11,
    "low": 20,
}
SEVERITY_ORDER = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
}


def stable_sample_key(row: sqlite3.Row) -> str:
    return "|".join(
        [
            row["nct_id"],
            str(row["from_version"]),
            str(row["to_version"]),
            row["category"],
            row["severity"],
            row["changed_paths_json"],
            row["raw_hash"] or "",
        ]
    )


def sample_hash(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode("utf-8")).hexdigest()


def load_rows(connection: sqlite3.Connection, seed: str) -> list[dict[str, str | int | None]]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          me.id AS materiality_event_id,
          me.nct_id,
          me.from_version,
          me.to_version,
          me.submitted_date,
          me.severity,
          me.category,
          me.changed_paths_json,
          me.raw_hash,
          er.event_id AS evidence_record_id
        FROM materiality_events me
        LEFT JOIN evidence_records er
          ON er.nct_id = me.nct_id
         AND er.from_version = me.from_version
         AND er.to_version = me.to_version
        WHERE me.severity IN ('critical', 'high', 'medium', 'low')
        """
    ).fetchall()

    by_severity: dict[str, list[dict[str, str | int | None]]] = {}
    for row in rows:
        key = stable_sample_key(row)
        digest = sample_hash(seed, key)
        item: dict[str, str | int | None] = {
            "materiality_event_id": row["materiality_event_id"],
            "stable_sample_key": key,
            "severity_stratum": row["severity"],
            "nct_id": row["nct_id"],
            "from_version": row["from_version"],
            "to_version": row["to_version"],
            "submitted_date": row["submitted_date"],
            "category": row["category"],
            "evidence_record_id": row["evidence_record_id"] or "",
            "sample_order_hash": digest,
        }
        by_severity.setdefault(row["severity"], []).append(item)

    sample: list[dict[str, str | int | None]] = []
    for severity, target in TARGETS.items():
        severity_rows = sorted(by_severity.get(severity, []), key=lambda item: str(item["sample_order_hash"]))
        for rank, item in enumerate(severity_rows[:target], start=1):
            item["stratum_rank"] = rank
            item["sample_key"] = f"{severity}-{rank:03d}"
            sample.append(item)

    return sorted(
        sample,
        key=lambda item: (SEVERITY_ORDER[str(item["severity_stratum"])], int(item["stratum_rank"])),
    )


def write_csv(rows: list[dict[str, str | int | None]], output: Path) -> None:
    fieldnames = [
        "materiality_event_id",
        "sample_key",
        "stable_sample_key",
        "severity_stratum",
        "nct_id",
        "from_version",
        "to_version",
        "submitted_date",
        "category",
        "evidence_record_id",
        "sample_order_hash",
        "stratum_rank",
    ]
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Draw the TrialDiff v0.2 calibration sample.")
    parser.add_argument("--db", default="trialdiff_breast_cancer_limit25.sqlite3")
    parser.add_argument("--out", default="CALIBRATION_SAMPLE_v0.2.csv")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()

    connection = sqlite3.connect(args.db)
    try:
        rows = load_rows(connection, args.seed)
    finally:
        connection.close()

    write_csv(rows, Path(args.out))
    print(f"seed={args.seed}")
    print(f"sample_rows={len(rows)}")
    counts: dict[str, int] = {}
    for row in rows:
        severity = str(row["severity_stratum"])
        counts[severity] = counts.get(severity, 0) + 1
    print(f"counts={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
