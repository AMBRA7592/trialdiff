#!/usr/bin/env python3
"""Validate a TrialDiff event-class Evidence Record package."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


EXPECTED_CLASS_COUNTS = {
    "primary_endpoint_changed_after_primary_completion_without_results_reconciliation": 10,
    "secondary_outcome_removed_after_primary_completion": 9,
    "enrollment_changed_to_zero": 1,
    "why_stopped_removed_in_terminal_context": 13,
    "outcome_edit_cooccurs_with_results_posting": 80,
}
EXPECTED_OVERLAPS = {1: 88, 2: 11, 3: 1}
THREE_CLASS_EVENT_ID = "evt_NCT04278144_v33_v34_bdd9f29ed71e"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", default="event_class_records_v0.1", help="Package directory.")
    parser.add_argument("--db", default=None, help="Optional SQLite DB for canonical_hash cross-checks.")
    args = parser.parse_args()

    package_dir = Path(args.package)
    records_dir = package_dir / "records"
    manifest_path = package_dir / "MANIFEST.sha256"
    validation_path = package_dir / "VALIDATION.md"
    if not records_dir.is_dir():
        raise SystemExit(f"missing records directory: {records_dir}")
    if not manifest_path.is_file():
        raise SystemExit(f"missing manifest: {manifest_path}")
    if not validation_path.is_file():
        raise SystemExit(f"missing validation note: {validation_path}")

    verify_manifest(package_dir, manifest_path)
    db_hashes = load_db_hashes(Path(args.db)) if args.db else {}

    records = []
    for path in sorted(records_dir.glob("*.json")):
        payload = path.read_bytes()
        record_hash = sha256_bytes(payload)
        record = json.loads(payload)
        validate_record(path, record)
        if db_hashes and db_hashes.get(record["event_id"]) != record_hash:
            raise SystemExit(f"{record['event_id']}: file hash does not match DB canonical_hash")
        records.append(record)

    validate_counts(records)
    print(f"records={len(records)}")
    print(f"trials={len({record['trial']['nct_id'] for record in records})}")
    print(f"class_counts={dict(sorted(class_counts(records).items()))}")
    print(f"overlaps={dict(sorted(overlap_counts(records).items()))}")
    print(f"three_class_record_present={has_three_class_record(records)}")
    print("manifest_ok=True")
    if db_hashes:
        print("db_canonical_hashes_ok=True")
    return 0


def verify_manifest(package_dir: Path, manifest_path: Path) -> None:
    seen_paths: set[str] = set()
    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            expected_hash, relative_path = line.split(maxsplit=1)
        except ValueError as exc:
            raise SystemExit(f"{manifest_path}:{line_number}: malformed manifest line") from exc
        path = package_dir / relative_path
        if not path.exists():
            raise SystemExit(f"{manifest_path}:{line_number}: missing file {relative_path}")
        actual_hash = sha256_bytes(path.read_bytes())
        if actual_hash != expected_hash:
            raise SystemExit(f"{manifest_path}:{line_number}: hash mismatch for {relative_path}")
        seen_paths.add(relative_path)

    expected_paths = {"VALIDATION.md"} | {
        f"records/{path.name}" for path in (package_dir / "records").glob("*.json")
    }
    missing = expected_paths - seen_paths
    extra = seen_paths - expected_paths
    if missing or extra:
        raise SystemExit(f"manifest path mismatch: missing={sorted(missing)} extra={sorted(extra)}")


def load_db_hashes(db_path: Path) -> dict[str, str]:
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("SELECT event_id, canonical_hash FROM evidence_records").fetchall()
    finally:
        connection.close()
    return {str(event_id): str(canonical_hash) for event_id, canonical_hash in rows}


def validate_record(path: Path, record: dict[str, Any]) -> None:
    if record.get("schema") != "trialdiff.evidence_record":
        raise SystemExit(f"{path}: unexpected schema")
    if path.stem != record.get("event_id"):
        raise SystemExit(f"{path}: filename does not match event_id")
    classification = record.get("classification") or {}
    event_classes = classification.get("event_classes")
    if not isinstance(event_classes, list) or not event_classes:
        raise SystemExit(f"{path}: event_classes must be a nonempty list")
    if event_classes != sorted(event_classes):
        raise SystemExit(f"{path}: event_classes are not sorted")
    if classification.get("calibration_status") != "uncalibrated":
        raise SystemExit(f"{path}: calibration_status is not uncalibrated")
    if "triage_label" not in classification:
        raise SystemExit(f"{path}: missing triage_label")
    if "patch" not in record or not record["patch"]:
        raise SystemExit(f"{path}: missing patch")
    if "claims_supported" not in record or not record["claims_supported"]:
        raise SystemExit(f"{path}: missing claims_supported")
    if "claims_not_supported" not in record or not record["claims_not_supported"]:
        raise SystemExit(f"{path}: missing claims_not_supported")


def validate_counts(records: list[dict[str, Any]]) -> None:
    counts = class_counts(records)
    overlaps = overlap_counts(records)
    if len(records) != 100:
        raise SystemExit(f"expected 100 records, found {len(records)}")
    if len({record["trial"]["nct_id"] for record in records}) != 52:
        raise SystemExit("expected 52 represented trials")
    if dict(counts) != EXPECTED_CLASS_COUNTS:
        raise SystemExit(f"class counts mismatch: {dict(counts)}")
    if dict(overlaps) != EXPECTED_OVERLAPS:
        raise SystemExit(f"overlap counts mismatch: {dict(overlaps)}")
    if not has_three_class_record(records):
        raise SystemExit(f"missing expected three-class record {THREE_CLASS_EVENT_ID}")


def class_counts(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(record["classification"]["event_classes"])
    return counts


def overlap_counts(records: list[dict[str, Any]]) -> Counter[int]:
    return Counter(len(record["classification"]["event_classes"]) for record in records)


def has_three_class_record(records: list[dict[str, Any]]) -> bool:
    return any(
        record["event_id"] == THREE_CLASS_EVENT_ID
        and len(record["classification"]["event_classes"]) == 3
        for record in records
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
