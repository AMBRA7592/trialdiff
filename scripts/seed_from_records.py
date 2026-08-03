#!/usr/bin/env python3
"""Seed a TrialDiff SQLite database from committed Evidence Record files.

This gives anyone a runnable local demo without the private corpus
databases: the committed ``event_class_records_v0.1.3/records/*.json`` files
carry enough data to populate ``trials``, ``trial_versions``, ``trial_patches``,
``materiality_events``, and ``evidence_records``.

Typical local-dev flow:

    python3 scripts/seed_from_records.py --db seed_demo.sqlite3
    python3 scripts/sqlite_to_postgres.py seed_demo.sqlite3 --truncate \
      --package-generation v0.1.3 --activate-generation --output seed_demo.sql
    psql "$DATABASE_URL" -f seed_demo.sql

Limitations (documented, not bugs): version snapshots (``record_json``) are
not part of exported records, so the patch inspector shows before-values as
missing for seeded data; study metadata for event-class records is limited
to what the record schema carries.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trialdiff.constants import Source  # noqa: E402
from trialdiff.db import TrialDiffStore, connect, init_db  # noqa: E402
from trialdiff.provenance import Provenance, canonical_json, sha256_text  # noqa: E402

SEED_TIMESTAMP = "1970-01-01T00:00:00Z"
KNOWN_SEVERITIES = {"critical", "high", "medium", "low", "ignore"}


def record_nct_id(record: dict) -> str:
    trial = record.get("trial") or record.get("study") or {}
    return trial["nct_id"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="seed_demo.sqlite3", help="SQLite database to create/populate.")
    parser.add_argument(
        "--source",
        action="append",
        help="Directory of record .json files. Repeatable. "
        "Defaults to event_class_records_v0.1.3/records/.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    sources = (
        [Path(s) for s in args.source]
        if args.source
        else [repo_root / "event_class_records_v0.1.3" / "records"]
    )

    init_db(args.db)
    connection = connect(args.db)
    counts = Counter()
    try:
        for source_dir in sources:
            if not source_dir.is_dir():
                print(f"skipping missing source dir: {source_dir}", file=sys.stderr)
                continue
            for path in sorted(source_dir.glob("evt_*.json")):
                raw_text = path.read_text(encoding="utf-8")
                record = json.loads(raw_text)
                schema = record.get("schema")
                if schema == "trialdiff.alpha_demo_record":
                    seed_alpha_record(connection, record, counts)
                elif schema == "trialdiff.evidence_record":
                    seed_evidence_record_file(connection, record, raw_text, counts)
                else:
                    print(f"skipping {path}: unknown schema {schema!r}", file=sys.stderr)
        connection.commit()
    finally:
        connection.close()

    print(f"db={args.db}")
    for key in ("trials", "versions", "patches", "materiality_events", "evidence_records"):
        print(f"{key}={counts[key]}")
    return 0


def seed_alpha_record(connection, record: dict, counts: Counter) -> None:
    study = record["study"]
    provenance = record["provenance"]
    classification = record["classification"]
    versions = record["versions"]
    nct_id = study["nct_id"]

    insert_trial(
        connection,
        counts,
        nct_id=nct_id,
        brief_title=study.get("title"),
        official_title=study.get("official_title"),
        lead_sponsor=study.get("lead_sponsor"),
        lead_sponsor_class=study.get("lead_sponsor_class"),
        current_record_hash=study.get("current_record_hash"),
        raw_hash=study.get("current_record_raw_hash") or "",
        source_url=study.get("official_v2_api_url") or study.get("clinicaltrials_gov_url") or "",
    )
    insert_versions_and_patch(connection, counts, record=record, nct_id=nct_id, versions=versions, provenance=provenance)
    insert_materiality_event(connection, counts, record=record)
    insert_evidence_row(
        connection,
        counts,
        record=record,
        canonical=record["canonical_evidence_record"],
        canonical_hash=provenance["evidence_canonical_hash"],
        evidence_version=provenance.get("evidence_version") or 1,
        source=provenance.get("evidence_source") or "derived_evidence_record",
        source_url=provenance.get("evidence_source_url") or f"trialdiff://evidence-record/{record['event_id']}",
    )


def seed_evidence_record_file(connection, record: dict, raw_text: str, counts: Counter) -> None:
    provenance = record["provenance"]
    classification = record["classification"]
    versions = record["versions"]
    nct_id = record["trial"]["nct_id"]

    insert_trial(
        connection,
        counts,
        nct_id=nct_id,
        brief_title=None,
        official_title=None,
        lead_sponsor=None,
        lead_sponsor_class=None,
        current_record_hash=None,
        raw_hash="",
        source_url=record["trial"].get("clinicaltrials_gov_url") or "",
    )
    insert_versions_and_patch(connection, counts, record=record, nct_id=nct_id, versions=versions, provenance=provenance)
    insert_materiality_event(connection, counts, record=record)
    insert_evidence_row(
        connection,
        counts,
        record=record,
        canonical=record,
        canonical_hash=sha256_text(raw_text),
        evidence_version=record.get("evidence_version") or 1,
        source="derived_evidence_record",
        source_url=f"trialdiff://evidence-record/{record['event_id']}",
    )


def insert_trial(connection, counts: Counter, *, nct_id: str, brief_title, official_title, lead_sponsor, lead_sponsor_class, current_record_hash, raw_hash: str, source_url: str) -> None:
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO trials (
          nct_id, brief_title, official_title, lead_sponsor, lead_sponsor_class,
          conditions_json, interventions_json, overall_status, phase_json, study_type,
          last_update_posted, first_submitted_date, has_results, current_record_json,
          current_record_hash, source, source_url, fetched_at, source_version, raw_hash
        ) VALUES (?, ?, ?, ?, ?, '[]', '[]', NULL, '[]', NULL, NULL, NULL, 0, '{}', ?, ?, ?, ?, NULL, ?)
        """,
        (
            nct_id,
            brief_title or nct_id,
            official_title,
            lead_sponsor,
            lead_sponsor_class,
            current_record_hash or "",
            "official_v2",
            source_url,
            SEED_TIMESTAMP,
            raw_hash,
        ),
    )
    counts["trials"] += cursor.rowcount if cursor.rowcount > 0 else 0
    if cursor.rowcount == 0 and brief_title:
        # A richer source (alpha study block) upgrades a placeholder row.
        connection.execute(
            """
            UPDATE trials SET brief_title=?, official_title=?, lead_sponsor=?, lead_sponsor_class=?
            WHERE nct_id=? AND brief_title=nct_id
            """,
            (brief_title, official_title, lead_sponsor, lead_sponsor_class, nct_id),
        )


def insert_versions_and_patch(connection, counts: Counter, *, record: dict, nct_id: str, versions: dict, provenance: dict) -> None:
    for version, record_hash, submitted in (
        (versions["from_version"], provenance.get("from_snapshot_hash"), None),
        (versions["to_version"], provenance.get("to_snapshot_hash"), versions.get("submitted_date")),
    ):
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO trial_versions (
              nct_id, version, submitted_date, overall_status, study_type, module_labels_json,
              review_not_passed, unposted_events_json, record_json, record_hash,
              source, source_url, fetched_at, source_version, raw_hash
            ) VALUES (?, ?, ?, NULL, NULL, '[]', 0, '[]', NULL, ?, ?, ?, ?, NULL, ?)
            """,
            (
                nct_id,
                version,
                submitted,
                record_hash,
                provenance.get("patch_source") or "ctgov_internal_history",
                provenance.get("patch_source_url") or "",
                SEED_TIMESTAMP,
                record_hash or "",
            ),
        )
        counts["versions"] += cursor.rowcount if cursor.rowcount > 0 else 0

    patch = record["patch"]
    modules = Counter()
    op_counts = Counter()
    for operation in patch:
        op_counts[operation.get("op", "unknown")] += 1
        parts = operation.get("path", "").split("/")
        if len(parts) > 2 and parts[1] == "protocolSection":
            modules[parts[2]] += 1
        elif len(parts) > 1 and parts[1]:
            modules[parts[1]] += 1
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO trial_patches (
          nct_id, from_version, to_version, patch_kind, patch_json, patch_hash,
          changed_paths_json, changed_modules_json, op_counts_json,
          source, source_url, fetched_at, source_version, raw_hash
        ) VALUES (?, ?, ?, 'ctgov_history_patch', ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """,
        (
            nct_id,
            versions["from_version"],
            versions["to_version"],
            canonical_json(patch),
            provenance["patch_hash"],
            canonical_json(record["changed_paths"]),
            canonical_json(sorted(modules)),
            canonical_json(dict(sorted(op_counts.items()))),
            provenance.get("patch_source") or "ctgov_internal_history",
            provenance.get("patch_source_url") or "",
            SEED_TIMESTAMP,
            provenance.get("patch_raw_hash") or "",
        ),
    )
    counts["patches"] += cursor.rowcount if cursor.rowcount > 0 else 0


def insert_materiality_event(connection, counts: Counter, *, record: dict) -> None:
    # Reuse the store's canonical INSERT so the seeded schema can never
    # drift from what the ingest pipeline writes.
    classification = record["classification"]
    versions = record["versions"]
    severity = classification.get("severity")
    if severity not in KNOWN_SEVERITIES:
        return
    event = {
        "nct_id": record_nct_id(record),
        "from_version": versions["from_version"],
        "to_version": versions["to_version"],
        "submitted_date": versions.get("submitted_date"),
        "timing_context": classification.get("timing_context"),
        "severity_pre_timing": classification.get("severity_pre_timing") or severity,
        "severity": severity,
        "category": classification.get("category") or "unknown_material_change",
        "categories": classification.get("categories") or [],
        "changed_paths": record.get("changed_paths") or [],
        "deterministic_rules": classification.get("deterministic_rules") or [],
        "value_signals": classification.get("value_signals") or [],
        "needs_human_review": severity in {"high", "critical"},
        "created_at": SEED_TIMESTAMP,
        "rule_set_hash": classification.get("triage_rule_set_hash") or classification.get("rule_set_hash") or "",
    }
    materiality_hash = record["provenance"].get("materiality_event_hash") or ""
    provenance = Provenance(
        source=Source.DERIVED_CLASSIFIER,
        source_url="trialdiff://classifier/materiality",
        fetched_at=SEED_TIMESTAMP,
        raw_hash=materiality_hash,
        source_version=materiality_hash or None,
    )
    before = connection.total_changes
    TrialDiffStore(connection).insert_materiality_event(event, provenance)
    counts["materiality_events"] += connection.total_changes - before


def insert_evidence_row(connection, counts: Counter, *, record: dict, canonical: dict, canonical_hash: str, evidence_version: int, source: str, source_url: str) -> None:
    # Reuse the store's canonical INSERT (TrialDiffStore.insert_evidence_record)
    # so the seeded schema can never drift from the generator's. The store
    # serializes `canonical` with canonical_json, which reproduces the exact
    # frozen bytes because those files ARE the canonical serialization.
    classification = record["classification"]
    versions = record["versions"]
    provenance = record["provenance"]
    store_record = {
        "event_id": record["event_id"],
        "nct_id": record_nct_id(record),
        "from_version": versions["from_version"],
        "to_version": versions["to_version"],
        "submitted_date": versions.get("submitted_date"),
        "timing_context": classification.get("timing_context"),
        "severity_pre_timing": classification.get("severity_pre_timing")
        or classification.get("severity")
        or "uncategorized",
        "severity": classification.get("severity") or "uncategorized",
        "category": classification.get("category") or "unknown_material_change",
        "categories": classification.get("categories") or [],
        "changed_paths": record.get("changed_paths") or [],
        "event_classes": classification.get("event_classes") or [],
        "deterministic_rules": classification.get("deterministic_rules") or [],
        "value_signals": classification.get("value_signals") or [],
        "claims_supported": record.get("claims_supported") or [],
        "claims_not_supported": record.get("claims_not_supported") or [],
        "review_question": record.get("review_question") or "",
        "citation_text": record.get("citation_text") or "",
        "canonical": canonical,
        "canonical_hash": canonical_hash,
        "evidence_version": evidence_version,
        "patch_hash": provenance["patch_hash"],
        "patch_source": provenance.get("patch_source") or "ctgov_internal_history",
        "patch_source_url": provenance.get("patch_source_url") or "",
        "patch_raw_hash": provenance.get("patch_raw_hash") or "",
        "from_snapshot_hash": provenance.get("from_snapshot_hash"),
        "to_snapshot_hash": provenance.get("to_snapshot_hash"),
        "materiality_event_hash": provenance.get("materiality_event_hash") or "",
        "rule_set_hash": classification.get("rule_set_hash") or "",
        "source": source,
        "source_url": source_url,
        "generated_at": SEED_TIMESTAMP,
    }
    counts["evidence_records"] += TrialDiffStore(connection).insert_evidence_record(store_record)


if __name__ == "__main__":
    raise SystemExit(main())
