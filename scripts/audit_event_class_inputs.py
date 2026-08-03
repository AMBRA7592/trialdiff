#!/usr/bin/env python3
"""Audit patch replay and the E4 sequential-removal correction over a frozen DB."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trialdiff.event_classes import (  # noqa: E402
    ENROLLMENT_CHANGED_TO_ZERO,
    OUTCOME_EDIT_WITH_RESULTS_SIGNAL,
    PRIMARY_ENDPOINT_CLEAN,
    SECONDARY_OUTCOME_REMOVED,
    WHY_STOPPED_REMOVED_TERMINAL,
    EventClassInputError,
    after_primary_completion,
    derive_to_record,
    event_classes_for_patch,
    get_path,
    has_results_reconciliation_signal,
    is_primary_endpoint_definition_path,
    is_primary_endpoint_item_path,
    is_secondary_outcome_item_removal,
    normalize_outcome,
    pointer_parts,
    primary_endpoint_definition_changed,
    secondary_outcome_item_removed_without_reindex,
)


EXPECTED_V03 = {
    "patches": 4485,
    "operations": {"add": 25076, "remove": 22710, "replace": 99332},
    "stored_to_records": 4385,
    "reconstructed_to_records": 100,
    "primary_relevant_patches": 148,
    "primary_after_completion": 73,
    "primary_results_cooccurring": 63,
    "primary_clean": 10,
    "primary_literal_vs_state_disagreements": [],
    "secondary_candidates": 16,
    "postcompletion_secondary_count_decreases": 11,
    "secondary_count_decreases_without_structural_candidate": [],
    "corrected_secondary_memberships": 12,
    "v02_vs_corrected_secondary_disagreements": [
        "NCT01224678_v109_v110",
        "NCT03094169_v11_v12",
        "NCT03734029_v29_v30",
    ],
    "classified_records": 97,
    "classified_trials": 54,
    "event_class_memberships": 109,
    "event_class_counts": {
        ENROLLMENT_CHANGED_TO_ZERO: 3,
        OUTCOME_EDIT_WITH_RESULTS_SIGNAL: 80,
        PRIMARY_ENDPOINT_CLEAN: 10,
        SECONDARY_OUTCOME_REMOVED: 12,
        WHY_STOPPED_REMOVED_TERMINAL: 4,
    },
    "event_class_overlap_counts": {1: 85, 2: 12},
    "secondary_whole_item_replace_operations": 0,
}


def historical_v02_primary_predicate(
    from_record: dict[str, Any],
    to_record: dict[str, Any],
    patch: list[dict[str, Any]],
) -> bool:
    """Reproduce the v0.2 fixed-index primary comparison for E4 audit."""
    for operation in patch:
        path = operation.get("path", "")
        if not (is_primary_endpoint_definition_path(path) or is_primary_endpoint_item_path(path)):
            continue
        parts = pointer_parts(path)
        if get_path(from_record, parts) != get_path(to_record, parts):
            return True
    return False


def historical_v02_secondary_predicate(
    from_record: dict[str, Any],
    to_record: dict[str, Any],
    patch: list[dict[str, Any]],
) -> bool:
    """Reproduce the defective literal-index resolver for E4 traceability."""
    removed_operations = [operation for operation in patch if is_secondary_outcome_item_removal(operation)]
    if not removed_operations:
        return False
    to_outcomes = get_path(
        to_record,
        ["protocolSection", "outcomesModule", "secondaryOutcomes"],
        [],
    ) or []
    to_normalized = {normalize_outcome(outcome) for outcome in to_outcomes}
    for operation in removed_operations:
        removed = get_path(from_record, pointer_parts(operation["path"]))
        normalized = normalize_outcome(removed)
        if normalized and normalized not in to_normalized:
            return True
    return False


def audit_secondary_removal_candidate(operation: dict[str, Any]) -> bool:
    """Define the audit denominator independently of the production predicate."""
    parts = pointer_parts(operation.get("path", ""))
    target = ["protocolSection", "outcomesModule", "secondaryOutcomes"]
    indexed_remove = (
        operation.get("op") == "remove"
        and len(parts) == 4
        and parts[:3] == target
        and parts[3].isdigit()
    )
    container_operation = bool(parts) and len(parts) <= len(target) and target[: len(parts)] == parts
    return indexed_remove or container_operation


def audit_secondary_whole_item_replacement(operation: dict[str, Any]) -> bool:
    parts = pointer_parts(operation.get("path", ""))
    return (
        operation.get("op") == "replace"
        and len(parts) == 4
        and parts[:3] == ["protocolSection", "outcomesModule", "secondaryOutcomes"]
        and parts[3].isdigit()
    )


def compute_input_audit(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT
          p.nct_id,
          p.from_version,
          p.to_version,
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

    operations: Counter[str] = Counter()
    stored_to_records = 0
    reconstructed_to_records = 0
    primary_relevant_patches = 0
    primary_after_completion = 0
    primary_results_cooccurring = 0
    primary_clean = 0
    primary_disagreements: list[str] = []
    secondary_candidates = 0
    corrected_secondary_memberships = 0
    historical_v02_secondary_memberships = 0
    disagreements: list[str] = []
    postcompletion_secondary_count_decreases = 0
    uncovered_secondary_count_decreases: list[str] = []
    classified_records = 0
    classified_trials: set[str] = set()
    event_class_memberships = 0
    event_class_counts: Counter[str] = Counter()
    event_class_overlap_counts: Counter[int] = Counter()
    secondary_whole_item_replace_operations = 0

    for row in rows:
        identity = f'{row["nct_id"]}_v{row["from_version"]}_v{row["to_version"]}'
        if not row["from_record_json"]:
            raise EventClassInputError(f"{identity}: missing FROM-version record")
        patch: list[dict[str, Any]] = json.loads(row["patch_json"])
        operations.update(str(operation.get("op", "<missing>")) for operation in patch)
        secondary_whole_item_replace_operations += sum(
            audit_secondary_whole_item_replacement(operation) for operation in patch
        )
        from_record = json.loads(row["from_record_json"])
        stored_to_record = json.loads(row["to_record_json"]) if row["to_record_json"] else None
        try:
            to_record = derive_to_record(from_record, stored_to_record, patch)
            event_classes = event_classes_for_patch(
                from_record=from_record,
                to_record=stored_to_record,
                patch=patch,
            )
        except EventClassInputError as error:
            raise EventClassInputError(f"{identity}: {error}") from error
        if event_classes:
            classified_records += 1
            classified_trials.add(row["nct_id"])
            event_class_memberships += len(event_classes)
            event_class_counts.update(event_classes)
            event_class_overlap_counts[len(event_classes)] += 1
        if stored_to_record is None:
            reconstructed_to_records += 1
        else:
            stored_to_records += 1

        has_primary_operation = any(
            is_primary_endpoint_definition_path(operation.get("path", ""))
            or is_primary_endpoint_item_path(operation.get("path", ""))
            for operation in patch
        )
        if has_primary_operation:
            primary_relevant_patches += 1
            corrected_primary = primary_endpoint_definition_changed(from_record, to_record, patch)
            historical_primary = historical_v02_primary_predicate(from_record, to_record, patch)
            if corrected_primary != historical_primary:
                primary_disagreements.append(identity)
            if after_primary_completion(from_record) and corrected_primary:
                primary_after_completion += 1
                if has_results_reconciliation_signal(
                    from_record=from_record,
                    to_record=to_record,
                    patch=patch,
                ):
                    primary_results_cooccurring += 1
                else:
                    primary_clean += 1

        has_secondary_removal = any(audit_secondary_removal_candidate(operation) for operation in patch)
        if after_primary_completion(from_record):
            from_secondary = get_path(
                from_record,
                ["protocolSection", "outcomesModule", "secondaryOutcomes"],
                [],
            )
            to_secondary = get_path(
                to_record,
                ["protocolSection", "outcomesModule", "secondaryOutcomes"],
                [],
            )
            if from_secondary is None:
                from_secondary = []
            if to_secondary is None:
                to_secondary = []
            if not isinstance(from_secondary, list) or not isinstance(to_secondary, list):
                raise EventClassInputError(f"{identity}: secondaryOutcomes is not an array")
            if len(from_secondary) > len(to_secondary):
                postcompletion_secondary_count_decreases += 1
                if not has_secondary_removal:
                    uncovered_secondary_count_decreases.append(identity)
        if not (after_primary_completion(from_record) and has_secondary_removal):
            continue
        secondary_candidates += 1
        try:
            corrected = secondary_outcome_item_removed_without_reindex(from_record, to_record, patch)
        except EventClassInputError as error:
            raise EventClassInputError(f"{identity}: {error}") from error
        historical = historical_v02_secondary_predicate(from_record, to_record, patch)
        corrected_secondary_memberships += int(corrected)
        historical_v02_secondary_memberships += int(historical)
        if corrected != historical:
            disagreements.append(identity)

    return {
        "patches": len(rows),
        "operations": dict(sorted(operations.items())),
        "stored_to_records": stored_to_records,
        "reconstructed_to_records": reconstructed_to_records,
        "primary_relevant_patches": primary_relevant_patches,
        "primary_after_completion": primary_after_completion,
        "primary_results_cooccurring": primary_results_cooccurring,
        "primary_clean": primary_clean,
        "primary_literal_vs_state_disagreements": primary_disagreements,
        "secondary_candidates": secondary_candidates,
        "postcompletion_secondary_count_decreases": postcompletion_secondary_count_decreases,
        "secondary_count_decreases_without_structural_candidate": uncovered_secondary_count_decreases,
        "corrected_secondary_memberships": corrected_secondary_memberships,
        "historical_v02_secondary_memberships": historical_v02_secondary_memberships,
        "v02_vs_corrected_secondary_disagreements": disagreements,
        "classified_records": classified_records,
        "classified_trials": len(classified_trials),
        "event_class_memberships": event_class_memberships,
        "event_class_counts": dict(sorted(event_class_counts.items())),
        "event_class_overlap_counts": dict(sorted(event_class_overlap_counts.items())),
        "secondary_whole_item_replace_operations": secondary_whole_item_replace_operations,
    }


def enforce_v03_expectations(stats: dict[str, Any]) -> None:
    mismatches = {
        key: {"expected": expected, "actual": stats.get(key)}
        for key, expected in EXPECTED_V03.items()
        if stats.get(key) != expected
    }
    if mismatches:
        raise EventClassInputError(
            f"v0.3 event-class input audit diverged: {json.dumps(mismatches, sort_keys=True)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Frozen SQLite working database.")
    parser.add_argument(
        "--expect-v0.3",
        dest="expect_v03",
        action="store_true",
        help="Enforce the frozen-corpus replay and E4 correction gates.",
    )
    args = parser.parse_args()
    connection = sqlite3.connect(args.db)
    try:
        try:
            stats = compute_input_audit(connection)
            if args.expect_v03:
                enforce_v03_expectations(stats)
        except EventClassInputError as error:
            raise SystemExit(f"Event-class input audit halted: {error}") from error
    finally:
        connection.close()
    print(json.dumps(stats, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
