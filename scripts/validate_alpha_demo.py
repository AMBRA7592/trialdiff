#!/usr/bin/env python3
"""Validate the frozen TrialDiff v0.1-alpha evidence demo package."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


REQUIRED_TOP_LEVEL_KEYS = {
    "schema",
    "demo_version",
    "event_id",
    "study",
    "versions",
    "classification",
    "changed_paths",
    "patch",
    "claims_supported",
    "claims_not_supported",
    "review_question",
    "provenance",
    "live_urls",
    "source_corpus",
}

REQUIRED_STUDY_KEYS = {
    "nct_id",
    "title",
    "lead_sponsor",
    "clinicaltrials_gov_url",
    "official_v2_api_url",
}

REQUIRED_CLASSIFICATION_KEYS = {
    "severity",
    "category",
    "timing_context",
    "deterministic_rules",
    "rule_set_hash",
}

REQUIRED_PROVENANCE_KEYS = {
    "evidence_canonical_hash",
    "patch_hash",
    "patch_source",
    "patch_source_url",
    "materiality_event_hash",
}

REQUIRED_NON_CLAIM = "That the change constitutes misconduct or wrongdoing."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", default="records", help="Directory containing exported record JSON files.")
    parser.add_argument("--manifest", default="MANIFEST.sha256", help="Manifest file to verify when present.")
    args = parser.parse_args()

    records_dir = Path(args.records)
    record_paths = sorted(records_dir.glob("evt_*.json"))
    if not 20 <= len(record_paths) <= 40:
        raise SystemExit(f"expected 20-40 exported records, found {len(record_paths)}")

    severities: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    for path in record_paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        validate_record(path, record)
        severities[record["classification"]["severity"]] += 1
        categories[record["classification"]["category"]] += 1

    manifest_path = Path(args.manifest)
    if manifest_path.exists():
        verify_manifest(manifest_path)

    print(f"records={len(record_paths)}")
    print(f"severities={dict(sorted(severities.items()))}")
    print(f"categories={dict(sorted(categories.items()))}")
    return 0


def validate_record(path: Path, record: dict) -> None:
    missing = REQUIRED_TOP_LEVEL_KEYS - set(record)
    if missing:
        raise SystemExit(f"{path}: missing top-level keys {sorted(missing)}")
    if record["schema"] != "trialdiff.alpha_demo_record":
        raise SystemExit(f"{path}: unexpected schema {record['schema']!r}")
    if path.stem != record["event_id"]:
        raise SystemExit(f"{path}: filename does not match event_id")
    if record["classification"]["severity"] not in {"critical", "high"}:
        raise SystemExit(f"{path}: exported record is not high/critical")
    if not record["changed_paths"]:
        raise SystemExit(f"{path}: changed_paths is empty")
    if not record["patch"]:
        raise SystemExit(f"{path}: patch is empty")
    if not record["claims_supported"]:
        raise SystemExit(f"{path}: claims_supported is empty")
    if REQUIRED_NON_CLAIM not in record["claims_not_supported"]:
        raise SystemExit(f"{path}: required non-claim is absent")
    if REQUIRED_STUDY_KEYS - set(record["study"]):
        raise SystemExit(f"{path}: missing study keys")
    if REQUIRED_CLASSIFICATION_KEYS - set(record["classification"]):
        raise SystemExit(f"{path}: missing classification keys")
    if REQUIRED_PROVENANCE_KEYS - set(record["provenance"]):
        raise SystemExit(f"{path}: missing provenance keys")


def verify_manifest(manifest_path: Path) -> None:
    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        expected_hash, relative_path = line.split(maxsplit=1)
        path = Path(relative_path)
        if not path.exists():
            raise SystemExit(f"{manifest_path}:{line_number}: missing file {relative_path}")
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise SystemExit(f"{manifest_path}:{line_number}: hash mismatch for {relative_path}")


if __name__ == "__main__":
    raise SystemExit(main())
