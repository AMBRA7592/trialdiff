from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any


BASE_TABLES = [
    "trials",
    "trial_snapshots",
    "trial_versions",
    "trial_patches",
    "materiality_events",
    "classifier_rules",
    "case_studies",
    "ingest_runs",
]

EVIDENCE_SOURCE_TABLE = "evidence_records"
EVIDENCE_STORE_TABLE = "evidence_record_store"

FULL_REPLACE_TABLES = (
    "evidence_record_supersessions",
    EVIDENCE_STORE_TABLE,
    "evidence_record_generations",
    *BASE_TABLES,
)

JSON_COLUMNS = {
    "conditions_json",
    "interventions_json",
    "phase_json",
    "current_record_json",
    "record_json",
    "module_labels_json",
    "unposted_events_json",
    "patch_json",
    "changed_paths_json",
    "changed_modules_json",
    "op_counts_json",
    "categories_json",
    "event_classes_json",
    "deterministic_rules_json",
    "value_signals_json",
    "claims_supported_json",
    "claims_not_supported_json",
    # canonical_json is intentionally NOT in this set: it must be exported as
    # opaque text so the exact bytes hashing to canonical_hash survive the
    # copy. Re-encoding (or a jsonb cast) would break hash verification.
    "op_filter_json",
    "value_filter_json",
    "query_json",
    "relaxation_json",
    "severity_counts_json",
}

BOOLEAN_COLUMNS = {
    "has_results",
    "is_active",
    "review_not_passed",
    "needs_human_review",
    "timing_sensitive",
    "active",
}

TIMESTAMPTZ_COLUMNS = {
    "fetched_at",
    "created_at",
    "verified_at",
    "started_at",
    "completed_at",
    "generated_at",
}

IDENTITY_TABLES = (
    "trial_snapshots",
    "trial_versions",
    "trial_patches",
    "materiality_events",
    "classifier_rules",
    "case_studies",
    "ingest_runs",
)

PACKAGE_GENERATION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")


def quote_text(value: Any) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def quote_json(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, str):
        parsed = json.loads(value)
    else:
        parsed = value
    encoded = json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{quote_text(encoded)}::jsonb"


def quote_value(column: str, value: Any) -> str:
    if value is None:
        return "NULL"
    if column in JSON_COLUMNS:
        return quote_json(value)
    if column in BOOLEAN_COLUMNS:
        return "true" if bool(value) else "false"
    if column in TIMESTAMPTZ_COLUMNS:
        return f"{quote_text(value)}::timestamptz"
    if isinstance(value, int | float):
        return str(value)
    return quote_text(value)


def batched(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return [row["name"] for row in rows]

def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def dump_table(
    *,
    connection: sqlite3.Connection,
    table: str,
    target_table: str | None = None,
    extra_values: dict[str, Any] | None = None,
    batch_size: int,
    output: list[str],
) -> None:
    if not table_exists(connection, table):
        return
    columns = table_columns(connection, table)
    extra_values = extra_values or {}
    target_columns = [*columns, *extra_values]
    quoted_columns = ", ".join(f'"{column}"' for column in target_columns)
    rows = connection.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        return

    values = []
    for row in rows:
        encoded = [quote_value(column, row[column]) for column in columns]
        encoded.extend(quote_value(column, value) for column, value in extra_values.items())
        values.append("(" + ", ".join(encoded) + ")")

    for batch in batched(values, batch_size):
        output.append(f"INSERT INTO {target_table or table} ({quoted_columns}) VALUES")
        output.append(",\n".join(batch))
        output.append(";\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scalar_count(connection: sqlite3.Connection, query: str) -> int:
    return int(connection.execute(query).fetchone()[0])


def generation_metadata(connection: sqlite3.Connection, sqlite_path: Path) -> dict[str, Any]:
    if not table_exists(connection, EVIDENCE_SOURCE_TABLE):
        raise ValueError("source database has no evidence_records table")
    evidence_rows = connection.execute(
        "SELECT nct_id, event_classes_json, rule_set_hash FROM evidence_records"
    ).fetchall()
    if not evidence_rows:
        raise ValueError("source database contains no evidence records")

    rule_set_hashes = {str(row["rule_set_hash"]) for row in evidence_rows}
    if len(rule_set_hashes) != 1 or len(next(iter(rule_set_hashes))) != 64:
        raise ValueError(
            "one package generation must contain exactly one nonempty 64-character rule_set_hash"
        )

    membership_count = 0
    for row in evidence_rows:
        event_classes = json.loads(row["event_classes_json"] or "[]")
        if not isinstance(event_classes, list):
            raise ValueError("event_classes_json must be an array")
        membership_count += len(event_classes)

    max_submitted_row = connection.execute(
        "SELECT max(submitted_date) FROM materiality_events"
    ).fetchone()
    severity_counts = {
        str(row["severity"]): int(row["count"])
        for row in connection.execute(
            "SELECT severity, count(*) AS count FROM materiality_events GROUP BY severity"
        ).fetchall()
    }
    return {
        "record_count": len(evidence_rows),
        "represented_trial_count": len({str(row["nct_id"]) for row in evidence_rows}),
        "membership_count": membership_count,
        "corpus_trial_count": scalar_count(connection, "SELECT count(*) FROM trials"),
        "corpus_patch_count": scalar_count(connection, "SELECT count(*) FROM trial_patches"),
        "material_event_count": scalar_count(connection, "SELECT count(*) FROM materiality_events"),
        "critical_event_count": scalar_count(
            connection,
            "SELECT count(*) FROM materiality_events WHERE severity = 'critical'",
        ),
        "high_event_count": scalar_count(
            connection,
            "SELECT count(*) FROM materiality_events WHERE severity = 'high'",
        ),
        "severity_counts_json": severity_counts,
        "corpus_max_submitted_date": max_submitted_row[0] if max_submitted_row else None,
        "rule_set_hash": next(iter(rule_set_hashes)),
        "source_database_sha256": file_sha256(sqlite_path),
    }


def generation_insert(package_generation: str, metadata: dict[str, Any]) -> list[str]:
    columns = [
        "package_generation",
        "is_active",
        "record_count",
        "represented_trial_count",
        "membership_count",
        "corpus_trial_count",
        "corpus_patch_count",
        "material_event_count",
        "critical_event_count",
        "high_event_count",
        "severity_counts_json",
        "corpus_max_submitted_date",
        "rule_set_hash",
        "source_database_sha256",
    ]
    values = {
        "package_generation": package_generation,
        "is_active": False,
        **metadata,
    }
    quoted_columns = ", ".join(f'"{column}"' for column in columns)
    quoted_values = ", ".join(quote_value(column, values[column]) for column in columns)
    return [
        f"INSERT INTO evidence_record_generations ({quoted_columns}) VALUES",
        f"({quoted_values});\n",
    ]


def generation_assertion(package_generation: str) -> list[str]:
    generation = quote_text(package_generation)
    return [
        "DO $$",
        "DECLARE",
        "  metadata evidence_record_generations%ROWTYPE;",
        "  actual_record_count integer;",
        "  actual_represented_trial_count integer;",
        "  actual_membership_count integer;",
        "  actual_rule_hash_count integer;",
        "  actual_rule_set_hash text;",
        "  actual_severity_counts jsonb;",
        "BEGIN",
        f"  SELECT * INTO STRICT metadata FROM evidence_record_generations WHERE package_generation = {generation};",
        "  SELECT",
        "    count(*)::integer,",
        "    count(DISTINCT nct_id)::integer,",
        "    coalesce(sum(jsonb_array_length(event_classes_json)), 0)::integer,",
        "    count(DISTINCT rule_set_hash)::integer,",
        "    min(rule_set_hash)",
        "  INTO actual_record_count, actual_represented_trial_count, actual_membership_count,",
        "    actual_rule_hash_count, actual_rule_set_hash",
        "  FROM evidence_record_store",
        f"  WHERE package_generation = {generation};",
        "",
        "  IF actual_record_count <> metadata.record_count",
        "     OR actual_represented_trial_count <> metadata.represented_trial_count",
        "     OR actual_membership_count <> metadata.membership_count",
        "     OR actual_rule_hash_count <> 1",
        "     OR actual_rule_set_hash IS DISTINCT FROM metadata.rule_set_hash THEN",
        "    RAISE EXCEPTION 'generation metadata mismatch for %: records %, trials %, memberships %, rule hashes %, rule hash %',",
        "      metadata.package_generation, actual_record_count, actual_represented_trial_count,",
        "      actual_membership_count, actual_rule_hash_count, actual_rule_set_hash;",
        "  END IF;",
        "",
        "  SELECT coalesce(jsonb_object_agg(severity, count ORDER BY severity), '{}'::jsonb)",
        "  INTO actual_severity_counts",
        "  FROM (",
        "    SELECT severity, count(*)::integer AS count",
        "    FROM materiality_events",
        "    GROUP BY severity",
        "  ) counts;",
        "",
        "  IF metadata.corpus_trial_count <> (SELECT count(*) FROM trials)",
        "     OR metadata.corpus_patch_count <> (SELECT count(*) FROM trial_patches)",
        "     OR metadata.material_event_count <> (SELECT count(*) FROM materiality_events)",
        "     OR metadata.critical_event_count <> (SELECT count(*) FROM materiality_events WHERE severity = 'critical')",
        "     OR metadata.high_event_count <> (SELECT count(*) FROM materiality_events WHERE severity = 'high')",
        "     OR metadata.severity_counts_json <> actual_severity_counts",
        "     OR metadata.corpus_max_submitted_date IS DISTINCT FROM (SELECT max(submitted_date) FROM materiality_events) THEN",
        "    RAISE EXCEPTION 'source corpus metadata does not match target corpus for generation %',",
        "      metadata.package_generation;",
        "  END IF;",
        "END",
        "$$;",
    ]


def supersession_insert(*, supersedes: str, package_generation: str) -> list[str]:
    old_generation = quote_text(supersedes)
    new_generation = quote_text(package_generation)
    return [
        "DO $$",
        "DECLARE",
        "  old_count integer;",
        "  new_count integer;",
        "  matched_count integer;",
        "BEGIN",
        f"  SELECT count(*) INTO old_count FROM evidence_record_store WHERE package_generation = {old_generation};",
        f"  SELECT count(*) INTO new_count FROM evidence_record_store WHERE package_generation = {new_generation};",
        "  SELECT count(*) INTO matched_count",
        "  FROM evidence_record_store old_record",
        "  JOIN evidence_record_store new_record",
        "    ON new_record.nct_id = old_record.nct_id",
        "   AND new_record.from_version = old_record.from_version",
        "   AND new_record.to_version = old_record.to_version",
        f"  WHERE old_record.package_generation = {old_generation}",
        f"    AND new_record.package_generation = {new_generation};",
        "  IF old_count = 0 OR old_count <> new_count OR matched_count <> old_count THEN",
        "    RAISE EXCEPTION 'supersession requires a complete one-to-one transition map: old %, new %, matched %',",
        "      old_count, new_count, matched_count;",
        "  END IF;",
        "END",
        "$$;",
        "INSERT INTO evidence_record_supersessions (superseded_event_id, successor_event_id)",
        "SELECT old_record.event_id, new_record.event_id",
        "FROM evidence_record_store old_record",
        "JOIN evidence_record_store new_record",
        "  ON new_record.nct_id = old_record.nct_id",
        " AND new_record.from_version = old_record.from_version",
        " AND new_record.to_version = old_record.to_version",
        f"WHERE old_record.package_generation = {old_generation}",
        f"  AND new_record.package_generation = {new_generation}",
        "ORDER BY old_record.event_id;\n",
    ]


def build_export(
    sqlite_path: Path,
    *,
    package_generation: str,
    truncate: bool,
    evidence_only: bool,
    supersedes: str | None,
    activate_generation: bool,
    batch_size: int,
) -> str:
    if not PACKAGE_GENERATION_RE.fullmatch(package_generation):
        raise ValueError("package generation must use vMAJOR.MINOR.PATCH format")
    if supersedes and not PACKAGE_GENERATION_RE.fullmatch(supersedes):
        raise ValueError("superseded generation must use vMAJOR.MINOR.PATCH format")
    if evidence_only and activate_generation:
        raise ValueError("additive evidence imports must be verified before separate activation")

    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        metadata = generation_metadata(connection, sqlite_path)
        output = [
            "-- Generated by scripts/sqlite_to_postgres.py",
            "-- Run postgres/migrations/*.sql before applying this export.",
            f"-- Evidence package generation: {package_generation}",
            "BEGIN;",
            # quote_text escapes only single quotes, which is correct solely
            # under standard_conforming_strings=on (the default since PG 9.1).
            # Pin it: under SCS=off, backslash escapes inside canonical_json
            # (\uXXXX from ensure_ascii) would corrupt with only a WARNING.
            "SET standard_conforming_strings = on;",
        ]
        if truncate:
            table_list = ", ".join(FULL_REPLACE_TABLES)
            output.append(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE;")

        if not evidence_only:
            for table in BASE_TABLES:
                dump_table(connection=connection, table=table, batch_size=batch_size, output=output)

        output.extend(generation_insert(package_generation, metadata))
        dump_table(
            connection=connection,
            table=EVIDENCE_SOURCE_TABLE,
            target_table=EVIDENCE_STORE_TABLE,
            extra_values={"package_generation": package_generation},
            batch_size=batch_size,
            output=output,
        )
        output.extend(generation_assertion(package_generation))

        if supersedes:
            output.extend(supersession_insert(supersedes=supersedes, package_generation=package_generation))

        if not evidence_only:
            for table in IDENTITY_TABLES:
                output.append(
                    "SELECT setval(pg_get_serial_sequence("
                    f"{quote_text(table)}, 'id'), "
                    f"COALESCE((SELECT max(id) FROM {table}), 1), "
                    f"COALESCE((SELECT max(id) FROM {table}), 0) > 0);"
                )

        if activate_generation:
            output.append(
                f"SELECT trialdiff_activate_evidence_generation({quote_text(package_generation)});"
            )

        output.append("COMMIT;")
        return "\n".join(output) + "\n"
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a TrialDiff SQLite database as Postgres-compatible INSERT statements.",
    )
    parser.add_argument("sqlite", type=Path, help="Path to the source SQLite database.")
    parser.add_argument("--output", type=Path, help="Destination .sql file. Defaults to stdout.")
    parser.add_argument(
        "--package-generation",
        required=True,
        help="Package release label stored separately from evidence_version (for example v0.1.2).",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Destructive full-database replacement for local/bootstrap use only.",
    )
    parser.add_argument(
        "--evidence-only",
        action="store_true",
        help="Add only one evidence generation; leaves corpus and previous evidence rows intact.",
    )
    parser.add_argument(
        "--supersedes",
        help="Previous package generation; requires a complete one-to-one transition mapping.",
    )
    parser.add_argument(
        "--activate-generation",
        action="store_true",
        help="Activate the imported generation in the same transaction (local/bootstrap use).",
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Rows per INSERT statement.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.truncate == args.evidence_only:
        parser.error("choose exactly one of --truncate or --evidence-only")
    if args.supersedes and not args.evidence_only:
        parser.error("--supersedes requires --evidence-only")
    if args.evidence_only and args.activate_generation:
        parser.error("--activate-generation is prohibited with --evidence-only; verify, then activate separately")
    sql = build_export(
        args.sqlite,
        package_generation=args.package_generation,
        truncate=args.truncate,
        evidence_only=args.evidence_only,
        supersedes=args.supersedes,
        activate_generation=args.activate_generation,
        batch_size=args.batch_size,
    )
    if args.output:
        args.output.write_text(sql, encoding="utf-8")
    else:
        sys.stdout.write(sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
