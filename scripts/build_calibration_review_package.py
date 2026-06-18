from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trialdiff.jsonpatch import MISSING, build_value_contexts, resolve_pointer


DEFAULT_SEED = "trialdiff-v0.2-review-order-a764e33"


def missing_to_json(value: Any) -> Any:
    if value is MISSING:
        return {"__missing__": True}
    if isinstance(value, dict):
        return {key: missing_to_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [missing_to_json(item) for item in value]
    return value


def load_sample(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def review_order_hash(seed: str, stable_sample_key: str) -> str:
    return hashlib.sha256(f"{seed}|{stable_sample_key}".encode("utf-8")).hexdigest()


def load_event_context(connection: sqlite3.Connection, materiality_event_id: str) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT
          me.id AS materiality_event_id,
          me.nct_id,
          me.from_version,
          me.to_version,
          me.submitted_date,
          me.severity,
          me.category,
          me.deterministic_rules_json,
          me.value_signals_json,
          me.timing_context,
          me.changed_paths_json,
          me.raw_hash AS materiality_event_hash,
          tp.patch_json,
          tp.patch_hash,
          tp.raw_hash AS patch_raw_hash,
          tp.source AS patch_source,
          tp.source_url AS patch_source_url,
          tv_from.overall_status AS from_overall_status,
          tv_from.submitted_date AS from_submitted_date,
          tv_from.record_json AS from_record_json,
          tv_from.record_hash AS from_record_hash,
          tv_from.raw_hash AS from_raw_hash,
          tv_from.source AS from_source,
          tv_from.source_url AS from_source_url,
          tv_to.submitted_date AS to_submitted_date,
          tv_to.record_hash AS to_record_hash,
          tv_to.raw_hash AS to_raw_hash,
          tv_to.source AS to_source,
          tv_to.source_url AS to_source_url,
          er.event_id AS evidence_record_id
        FROM materiality_events me
        JOIN trial_patches tp
          ON tp.nct_id = me.nct_id
         AND tp.from_version = me.from_version
         AND tp.to_version = me.to_version
        JOIN trial_versions tv_from
          ON tv_from.nct_id = me.nct_id
         AND tv_from.version = me.from_version
        JOIN trial_versions tv_to
          ON tv_to.nct_id = me.nct_id
         AND tv_to.version = me.to_version
        LEFT JOIN evidence_records er
          ON er.nct_id = me.nct_id
         AND er.from_version = me.from_version
         AND er.to_version = me.to_version
        WHERE me.id = ?
        """,
        (materiality_event_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No materiality event found for id={materiality_event_id}")
    return row


def build_review_record(review_id: str, sample_row: dict[str, str], db_row: sqlite3.Row, order_hash: str) -> dict[str, Any]:
    from_record = json.loads(db_row["from_record_json"])
    patch = json.loads(db_row["patch_json"])
    contexts = build_value_contexts(from_record, patch)
    from_status_module = resolve_pointer(from_record, "/protocolSection/statusModule", default={})

    return {
        "review_record_id": review_id,
        "sample_commit_context": {
            "rubric_commit": "a764e33",
            "sample_plan_commit": "511429a",
            "sample_draw_commit": "6a5043e",
        },
        "source_record": {
            "nct_id": db_row["nct_id"],
            "from_version": db_row["from_version"],
            "to_version": db_row["to_version"],
            "from_submitted_date": db_row["from_submitted_date"],
            "to_submitted_date": db_row["to_submitted_date"],
            "patch_submitted_date": db_row["submitted_date"],
        },
        "changed_paths": json.loads(db_row["changed_paths_json"]),
        "patch_operations": [
            {
                "op": context.op,
                "path": context.path,
                "old_value": missing_to_json(context.old_value),
                "new_value": missing_to_json(context.new_value),
            }
            for context in contexts
        ],
        "from_version_status_fields": {
            "overall_status_column": db_row["from_overall_status"],
            "status_module": from_status_module,
        },
        "provenance": {
            "patch_hash": db_row["patch_hash"],
            "patch_raw_hash": db_row["patch_raw_hash"],
            "patch_source": db_row["patch_source"],
            "patch_source_url": db_row["patch_source_url"],
            "from_record_hash": db_row["from_record_hash"],
            "from_raw_hash": db_row["from_raw_hash"],
            "from_source": db_row["from_source"],
            "from_source_url": db_row["from_source_url"],
            "to_record_hash": db_row["to_record_hash"],
            "to_raw_hash": db_row["to_raw_hash"],
            "to_source": db_row["to_source"],
            "to_source_url": db_row["to_source_url"],
        },
        "review_instructions": {
            "rubric": "Apply SEVERITY_RUBRIC_v0.2.md at commit a764e33.",
            "do_not_infer": [
                "misconduct",
                "sponsor intent",
                "manuscript disclosure status",
                "regulatory compliance or non-compliance",
            ],
            "output_required": [
                "assigned_tier",
                "one_line_change_characterization",
                "one_line_rationale",
                "driving_paths",
                "ambiguous_or_insufficient_evidence_flag",
            ],
        },
        "review_order_hash": order_hash,
    }


def build_crosswalk_row(review_id: str, sample_row: dict[str, str], db_row: sqlite3.Row, order_hash: str) -> dict[str, Any]:
    return {
        "review_record_id": review_id,
        "materiality_event_id": sample_row["materiality_event_id"],
        "sample_key": sample_row["sample_key"],
        "stable_sample_key": sample_row["stable_sample_key"],
        "severity_stratum": sample_row["severity_stratum"],
        "trialdiff_severity": db_row["severity"],
        "trialdiff_category": db_row["category"],
        "nct_id": db_row["nct_id"],
        "from_version": db_row["from_version"],
        "to_version": db_row["to_version"],
        "submitted_date": db_row["submitted_date"],
        "evidence_record_id": db_row["evidence_record_id"] or "",
        "deterministic_rules_json": db_row["deterministic_rules_json"],
        "value_signals_json": db_row["value_signals_json"],
        "trialdiff_timing_context": db_row["timing_context"],
        "materiality_event_hash": db_row["materiality_event_hash"],
        "sample_order_hash": sample_row["sample_order_hash"],
        "review_order_hash": order_hash,
    }


def write_jsonl(rows: list[dict[str, Any]], output: Path) -> None:
    with output.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True, separators=(",", ":")))
            file.write("\n")


def write_crosswalk(rows: list[dict[str, Any]], output: Path) -> None:
    fieldnames = [
        "review_record_id",
        "materiality_event_id",
        "sample_key",
        "stable_sample_key",
        "severity_stratum",
        "trialdiff_severity",
        "trialdiff_category",
        "nct_id",
        "from_version",
        "to_version",
        "submitted_date",
        "evidence_record_id",
        "deterministic_rules_json",
        "value_signals_json",
        "trialdiff_timing_context",
        "materiality_event_hash",
        "sample_order_hash",
        "review_order_hash",
    ]
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build blinded TrialDiff v0.2 calibration review package.")
    parser.add_argument("--db", default="trialdiff_breast_cancer_limit25.sqlite3")
    parser.add_argument("--sample", default="CALIBRATION_SAMPLE_v0.2.csv")
    parser.add_argument("--out", default="CALIBRATION_REVIEW_PACKAGE_v0.2.jsonl")
    parser.add_argument("--crosswalk", default="CALIBRATION_REVIEW_CROSSWALK_PRIVATE_v0.2.csv")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()

    sample = load_sample(Path(args.sample))
    ordered = sorted(sample, key=lambda row: review_order_hash(args.seed, row["stable_sample_key"]))

    connection = sqlite3.connect(args.db)
    connection.row_factory = sqlite3.Row
    review_rows: list[dict[str, Any]] = []
    crosswalk_rows: list[dict[str, Any]] = []
    try:
        for index, sample_row in enumerate(ordered, start=1):
            review_id = f"rec_{index:03d}"
            order_hash = review_order_hash(args.seed, sample_row["stable_sample_key"])
            db_row = load_event_context(connection, sample_row["materiality_event_id"])
            review_rows.append(build_review_record(review_id, sample_row, db_row, order_hash))
            crosswalk_rows.append(build_crosswalk_row(review_id, sample_row, db_row, order_hash))
    finally:
        connection.close()

    write_jsonl(review_rows, Path(args.out))
    write_crosswalk(crosswalk_rows, Path(args.crosswalk))
    print(f"seed={args.seed}")
    print(f"review_rows={len(review_rows)}")
    print(f"review_package={args.out}")
    print(f"private_crosswalk={args.crosswalk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
