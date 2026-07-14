#!/usr/bin/env python3
"""Export the TrialDiff v0.1-alpha evidence demo record set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any


DEMO_VERSION = "v0.1-alpha"
LIVE_BASE_URL = "https://trialdiff.vercel.app"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default="trialdiff_breast_cancer_limit25.sqlite3",
        help="SQLite database containing generated Evidence Records.",
    )
    parser.add_argument(
        "--out",
        default="records",
        help="Output directory for exported records.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Number of selected high/critical Evidence Records to export.",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Only remove files this exporter could have written; never wipe
    # arbitrary JSON from a mistyped --out directory.
    for old in out_dir.glob("evt_*.json"):
        old.unlink()

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = list(select_records(connection, args.limit))
        counts = corpus_counts(connection)
    finally:
        connection.close()

    for row in rows:
        record = build_export_record(dict(row), counts=counts, db_name=db_path.name)
        target = out_dir / f"{record['event_id']}.json"
        target.write_text(
            json.dumps(record, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

    print(f"exported={len(rows)}\tdirectory={out_dir}")
    return 0


def select_records(connection: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
          e.*,
          t.brief_title,
          t.official_title,
          t.lead_sponsor,
          t.lead_sponsor_class,
          t.source_url AS trial_source_url,
          t.current_record_hash,
          t.raw_hash AS current_record_raw_hash
        FROM evidence_records e
        JOIN trials t ON t.nct_id = e.nct_id
        WHERE e.severity IN ('critical', 'high')
        ORDER BY
          CASE e.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END,
          CASE e.timing_context
            WHEN 'post_recruitment' THEN 1
            WHEN 'late_recruitment' THEN 2
            WHEN 'early_recruitment' THEN 3
            WHEN 'pre_recruitment' THEN 4
            ELSE 5
          END,
          e.submitted_date DESC,
          e.event_id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def corpus_counts(connection: sqlite3.Connection) -> dict[str, int]:
    queries = {
        "trials": "SELECT count(*) FROM trials",
        "patches": "SELECT count(*) FROM trial_patches",
        "materiality_events": "SELECT count(*) FROM materiality_events",
        "evidence_records": "SELECT count(*) FROM evidence_records",
    }
    return {
        name: int(connection.execute(sql).fetchone()[0])
        for name, sql in queries.items()
    }


def build_export_record(row: dict[str, Any], *, counts: dict[str, int], db_name: str) -> dict[str, Any]:
    canonical = json.loads(row["canonical_json"])
    changed_paths = json.loads(row["changed_paths_json"])
    deterministic_rules = json.loads(row["deterministic_rules_json"])
    value_signals = json.loads(row["value_signals_json"])
    claims_supported = json.loads(row["claims_supported_json"])
    claims_not_supported = json.loads(row["claims_not_supported_json"])
    categories = json.loads(row["categories_json"])
    patch = canonical["patch"]
    event_id = row["event_id"]
    nct_id = row["nct_id"]
    title = row["brief_title"] or row["official_title"] or ""

    return {
        "schema": "trialdiff.alpha_demo_record",
        "demo_version": DEMO_VERSION,
        "event_id": event_id,
        "study": {
            "nct_id": nct_id,
            "title": title,
            "official_title": row["official_title"],
            "lead_sponsor": row["lead_sponsor"],
            "lead_sponsor_class": row["lead_sponsor_class"],
            "clinicaltrials_gov_url": f"https://clinicaltrials.gov/study/{nct_id}",
            "official_v2_api_url": row["trial_source_url"],
            "current_record_hash": row["current_record_hash"],
            "current_record_raw_hash": row["current_record_raw_hash"],
        },
        "versions": canonical["versions"],
        "classification": {
            "severity_pre_timing": row["severity_pre_timing"],
            "severity": row["severity"],
            "category": row["category"],
            "categories": categories,
            "timing_context": row["timing_context"],
            "deterministic_rules": deterministic_rules,
            "value_signals": value_signals,
            "rule_set_hash": row["rule_set_hash"],
        },
        "changed_paths": changed_paths,
        "patch": patch,
        "claims_supported": claims_supported,
        "claims_not_supported": claims_not_supported,
        "review_question": row["review_question"],
        "provenance": {
            "evidence_version": row["evidence_version"],
            "evidence_canonical_hash": row["canonical_hash"],
            "evidence_source": row["source"],
            "evidence_source_url": row["source_url"],
            "patch_hash": row["patch_hash"],
            "patch_source": row["patch_source"],
            "patch_source_url": row["patch_source_url"],
            "patch_raw_hash": row["patch_raw_hash"],
            "from_snapshot_hash": row["from_snapshot_hash"],
            "to_snapshot_hash": row["to_snapshot_hash"],
            "materiality_event_hash": row["materiality_event_hash"],
        },
        "live_urls": {
            "evidence_page": f"{LIVE_BASE_URL}/events/{event_id}",
            "canonical_json": f"{LIVE_BASE_URL}/events/{event_id}.json",
            "trial_page": f"{LIVE_BASE_URL}/trials/{nct_id}",
        },
        "citation_text": row["citation_text"],
        "source_corpus": {
            "name": "TrialDiff v0.1-alpha 25-study breast cancer corpus",
            "database": db_name,
            "selection": (
                "All critical Evidence Records first, followed by highest-priority high Evidence Records "
                "ordered by post/late/early/pre timing and submitted date, capped at 40 records."
            ),
            "counts": counts,
            "note": (
                "The originally planned 100-study corpus remains a later expansion because the local "
                "100-study SQLite file was not reliably readable during alpha freeze."
            ),
        },
        "canonical_evidence_record": canonical,
    }


if __name__ == "__main__":
    raise SystemExit(main())
