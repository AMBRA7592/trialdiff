#!/usr/bin/env python3
"""Recompute the primary-endpoint/reconciliation boundary over all patches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trialdiff.event_classes import (  # noqa: E402
    after_primary_completion,
    derive_to_record,
    has_results_reconciliation_signal,
    primary_endpoint_definition_changed,
)


def compute_boundary_stats(connection: sqlite3.Connection) -> dict[str, int]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          p.patch_json,
          from_version.record_json AS from_record_json,
          to_version.record_json AS to_record_json
        FROM trial_patches p
        LEFT JOIN trial_versions from_version
          ON from_version.nct_id=p.nct_id
         AND from_version.version=p.from_version
        LEFT JOIN trial_versions to_version
          ON to_version.nct_id=p.nct_id
         AND to_version.version=p.to_version
        ORDER BY p.nct_id, p.from_version, p.to_version
        """
    ).fetchall()
    stats = {
        "patches": len(rows),
        "missing_from_record": 0,
        "inclusive_primary_after_completion": 0,
        "results_cooccurring": 0,
        "clean": 0,
    }
    for row in rows:
        if not row["from_record_json"]:
            stats["missing_from_record"] += 1
            continue
        patch: list[dict[str, Any]] = json.loads(row["patch_json"])
        from_record = json.loads(row["from_record_json"])
        stored_to_record = json.loads(row["to_record_json"]) if row["to_record_json"] else None
        to_record = derive_to_record(from_record, stored_to_record, patch)
        if not (
            after_primary_completion(from_record)
            and primary_endpoint_definition_changed(from_record, to_record, patch)
        ):
            continue
        stats["inclusive_primary_after_completion"] += 1
        if has_results_reconciliation_signal(
            from_record=from_record,
            to_record=to_record,
            patch=patch,
        ):
            stats["results_cooccurring"] += 1
        else:
            stats["clean"] += 1
    if stats["inclusive_primary_after_completion"] != (
        stats["results_cooccurring"] + stats["clean"]
    ):
        raise RuntimeError("boundary counts do not partition the inclusive flag")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Frozen SQLite working database.")
    args = parser.parse_args()
    connection = sqlite3.connect(args.db)
    try:
        stats = compute_boundary_stats(connection)
    finally:
        connection.close()
    for key, value in stats.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
