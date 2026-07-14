#!/usr/bin/env python3
"""Validate a TrialDiff event-class Evidence Record package.

Structural checks (schema, event classes, claims, manifest, canonical form)
always run. Count expectations are read from an ``expected_stats.json``
sidecar in the package directory when present; without a sidecar the stats
are printed but not enforced.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


def canonical_json(value: Any) -> str:
    # Must match trialdiff.provenance.canonical_json byte-for-byte.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", default="event_class_records_v0.1.1", help="Package directory.")
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
        if payload.decode("utf-8") != canonical_json(record):
            raise SystemExit(f"{path}: file bytes are not the canonical JSON serialization")
        if db_hashes and db_hashes.get(record["event_id"]) != record_hash:
            raise SystemExit(f"{record['event_id']}: file hash does not match DB canonical_hash")
        records.append(record)

    if not records:
        raise SystemExit(f"no records found in {records_dir}")

    expected = load_expected_stats(package_dir)
    if expected is not None:
        validate_counts(records, expected)

    print(f"records={len(records)}")
    print(f"trials={len({record['trial']['nct_id'] for record in records})}")
    print(f"class_counts={dict(sorted(class_counts(records).items()))}")
    print(f"overlaps={dict(sorted(overlap_counts(records).items()))}")
    print(f"max_class_overlap={max(overlap_counts(records))}")
    print("manifest_ok=True")
    print("canonical_form_ok=True")
    print(f"expected_stats={'enforced' if expected is not None else 'absent (stats not enforced)'}")
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

    required_paths = {"VALIDATION.md"} | {
        f"records/{path.name}" for path in (package_dir / "records").glob("*.json")
    }
    optional_paths = {"expected_stats.json"}
    missing = required_paths - seen_paths
    extra = seen_paths - (required_paths | optional_paths)
    if missing or extra:
        raise SystemExit(f"manifest path mismatch: missing={sorted(missing)} extra={sorted(extra)}")


def load_db_hashes(db_path: Path) -> dict[str, str]:
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("SELECT event_id, canonical_hash FROM evidence_records").fetchall()
    finally:
        connection.close()
    return {str(event_id): str(canonical_hash) for event_id, canonical_hash in rows}


def load_expected_stats(package_dir: Path) -> dict[str, Any] | None:
    sidecar = package_dir / "expected_stats.json"
    if not sidecar.is_file():
        return None
    return json.loads(sidecar.read_text(encoding="utf-8"))


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


def validate_counts(records: list[dict[str, Any]], expected: dict[str, Any]) -> None:
    counts = class_counts(records)
    overlaps = overlap_counts(records)
    if "records" in expected and len(records) != expected["records"]:
        raise SystemExit(f"expected {expected['records']} records, found {len(records)}")
    trials = len({record["trial"]["nct_id"] for record in records})
    if "trials" in expected and trials != expected["trials"]:
        raise SystemExit(f"expected {expected['trials']} represented trials, found {trials}")
    if "class_counts" in expected and dict(counts) != dict(expected["class_counts"]):
        raise SystemExit(f"class counts mismatch: {dict(counts)}")
    if "overlap_counts" in expected:
        expected_overlaps = {int(size): count for size, count in expected["overlap_counts"].items()}
        if dict(overlaps) != expected_overlaps:
            raise SystemExit(f"overlap counts mismatch: {dict(overlaps)}")
    showcase = expected.get("showcase")
    if showcase:
        found = any(
            record["event_id"] == showcase["event_id"]
            and len(record["classification"]["event_classes"]) == showcase["class_count"]
            for record in records
        )
        if not found:
            raise SystemExit(
                f"missing expected showcase record {showcase['event_id']} "
                f"with {showcase['class_count']} classes"
            )


def class_counts(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(record["classification"]["event_classes"])
    return counts


def overlap_counts(records: list[dict[str, Any]]) -> Counter[int]:
    return Counter(len(record["classification"]["event_classes"]) for record in records)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
