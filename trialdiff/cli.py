from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from trialdiff.classifier.materiality import (
    V021_TRIAGE_RULE_SET_HASH,
    ClassifierRule,
    classify_patch,
    provenance_for_event,
    rule_set_hash,
)
from trialdiff.corpus import select_breast_cancer_corpus, write_corpus
from trialdiff.db import TrialDiffStore, connect, init_db
from trialdiff.evidence import EVIDENCE_VERSION, generate_evidence_records
from trialdiff.ingest import ingest_nct_ids
from trialdiff.verify import verify_record_file


def read_nct_ids(args: argparse.Namespace) -> list[str]:
    ids: list[str] = []
    if args.nct:
        ids.extend(args.nct)
    if args.nct_file:
        path = Path(args.nct_file)
        ids.extend(line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    normalized = []
    seen = set()
    for nct_id in ids:
        if not nct_id:
            continue
        value = nct_id.strip().upper()
        if value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def cmd_init_db(args: argparse.Namespace) -> int:
    init_db(args.db)
    print(f"Initialized database at {args.db}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    nct_ids = read_nct_ids(args)
    if not nct_ids:
        print("No NCT IDs provided.", file=sys.stderr)
        return 2
    init_db(args.db)
    connection = connect(args.db)
    try:
        store = TrialDiffStore(connection)
        results = ingest_nct_ids(
            nct_ids=nct_ids,
            store=store,
            fetch_internal=not args.no_internal,
            corpus_label=args.corpus_label,
            delay_seconds=args.delay_seconds,
        )
        connection.commit()
    finally:
        connection.close()
    for result in results:
        status = "ok" if not result.error else f"error: {result.error}"
        print(
            f"{result.nct_id}\tofficial={result.official_snapshot_stored}\t"
            f"internal={result.internal_history_stored}\tpatches={result.patch_count}\t{status}"
        )
    return 0 if all(result.error is None for result in results) else 1


def cmd_classify(args: argparse.Namespace) -> int:
    init_db(args.db)
    classified = 0
    skipped = 0
    connection = connect(args.db)
    try:
        store = TrialDiffStore(connection)
        if args.force:
            deleted = store.delete_materiality_events(args.nct)
            print(f"deleted_existing_events={deleted}")
        rules = [ClassifierRule.from_row(row) for row in store.load_active_rules()]
        active_hash = rule_set_hash(rules)
        if active_hash != V021_TRIAGE_RULE_SET_HASH:
            print(
                f"WARNING: active rule set hash {active_hash} does not match the committed "
                f"v0.2.1 rule set {V021_TRIAGE_RULE_SET_HASH}; the rule table has drifted "
                "from the migrations and generated events will carry the non-standard hash. "
                "Re-create the database (or restore the seeds) to reconverge.",
                file=sys.stderr,
            )
        patch_rows = store.iter_patches(args.nct)
        for patch_row in patch_rows:
            from_record = store.get_version_record(patch_row["nct_id"], patch_row["from_version"])
            if from_record is None:
                skipped += 1
                continue
            patch = json.loads(patch_row["patch_json"])
            event = classify_patch(
                nct_id=patch_row["nct_id"],
                from_version=patch_row["from_version"],
                to_version=patch_row["to_version"],
                from_record=from_record,
                patch=patch,
                rules=rules,
                submitted_date=store.get_version_submitted_date(patch_row["nct_id"], patch_row["to_version"]),
            )
            if event is None:
                continue
            store.insert_materiality_event(event.as_dict(), provenance_for_event(event))
            classified += 1
        connection.commit()
    finally:
        connection.close()
    print(f"classified={classified}\tskipped_missing_from_record={skipped}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    connection = connect(args.db)
    try:
        rows = connection.execute(
            """
            SELECT from_version, to_version, submitted_date, severity, severity_pre_timing,
                   timing_context, category, categories_json, deterministic_rules_json,
                   value_signals_json, changed_paths_json
            FROM materiality_events
            WHERE nct_id=?
            ORDER BY from_version, to_version,
              CASE severity
                WHEN 'critical' THEN 4
                WHEN 'high' THEN 3
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 1
                ELSE 0
              END DESC
            """,
            (args.nct,),
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        print(f"No materiality events found for {args.nct}. Run ingest and classify first.")
        return 1
    print(f"TrialDiff materiality timeline for {args.nct}")
    for row in rows:
        categories = ", ".join(json.loads(row["categories_json"]))
        rules = ", ".join(json.loads(row["deterministic_rules_json"]))
        paths = json.loads(row["changed_paths_json"])
        print(
            f"\n{row['from_version']} -> {row['to_version']} | {row['severity']} "
            f"(base={row['severity_pre_timing']}, timing={row['timing_context']})"
        )
        print(f"category: {row['category']}")
        if categories:
            print(f"all categories: {categories}")
        if rules:
            print(f"rules: {rules}")
        print("paths:")
        for path in paths[: args.max_paths]:
            print(f"  - {path}")
        if len(paths) > args.max_paths:
            print(f"  ... {len(paths) - args.max_paths} more")
    return 0


def cmd_select_corpus(args: argparse.Namespace) -> int:
    selection = select_breast_cancer_corpus(
        limit=args.limit,
        query_cond=args.condition,
        cutoff_date=args.cutoff_date,
        min_versions=args.min_versions,
        page_size=args.page_size,
        max_pages=args.max_pages,
        delay_seconds=args.delay_seconds,
    )
    json_path, txt_path = write_corpus(selection, args.output_dir, args.stem)
    print(f"selected={len(selection.selected)}")
    print(f"candidate_count={selection.candidate_count}")
    print(f"locally_eligible_count={selection.locally_eligible_count}")
    print(f"errors={len(selection.errors)}")
    print(f"json={json_path}")
    print(f"txt={txt_path}")
    return 0 if selection.selected else 1


def cmd_generate_evidence(args: argparse.Namespace) -> int:
    init_db(args.db)
    connection = connect(args.db)
    try:
        store = TrialDiffStore(connection)
        result = generate_evidence_records(
            store,
            nct_id=args.nct,
            force=args.force,
            evidence_version=args.evidence_version,
        )
        connection.commit()
    finally:
        connection.close()
    print(
        f"generated={result.generated}\tskipped_existing={result.skipped}\tdeleted_existing={result.deleted}"
    )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    failures = 0
    for raw_path in args.paths:
        path = Path(raw_path)
        targets = sorted(path.glob("*.json")) if path.is_dir() else [path]
        if not targets:
            print(f"{path}: no .json records found")
            failures += 1
            continue
        for target in targets:
            result = verify_record_file(target)
            status = "PASS" if result.ok else "FAIL"
            print(f"{status}\t{target}\tschema={result.schema}")
            for name, passed, detail in result.checks:
                marker = "ok" if passed else "MISMATCH"
                show_detail = detail and (not passed or args.verbose)
                print(f"  {name}: {marker}" + (f" ({detail})" if show_detail else ""))
            if args.verbose:
                for note in result.notes:
                    print(f"  note: {note}")
            if not result.ok:
                failures += 1
    print(f"verified={'PASS' if failures == 0 else 'FAIL'}\tfailures={failures}")
    return 0 if failures == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trialdiff")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Initialize the SQLite database.")
    init_parser.add_argument("--db", default="trialdiff.sqlite3")
    init_parser.set_defaults(func=cmd_init_db)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest one or more NCT IDs.")
    ingest_parser.add_argument("--db", default="trialdiff.sqlite3")
    ingest_parser.add_argument("--nct", action="append", help="NCT ID to ingest. Repeatable.")
    ingest_parser.add_argument("--nct-file", help="File containing one NCT ID per line.")
    ingest_parser.add_argument("--no-internal", action="store_true", help="Skip undocumented internal history backfill.")
    ingest_parser.add_argument("--corpus-label", help="Optional label for the ingest run.")
    ingest_parser.add_argument("--delay-seconds", type=float, default=0.0, help="Sleep between NCT ingests.")
    ingest_parser.set_defaults(func=cmd_ingest)

    classify_parser = subparsers.add_parser("classify", help="Classify stored patches into materiality events.")
    classify_parser.add_argument("--db", default="trialdiff.sqlite3")
    classify_parser.add_argument("--nct", help="Optional NCT ID to classify.")
    classify_parser.add_argument("--force", action="store_true", help="Delete existing derived events before classifying.")
    classify_parser.set_defaults(func=cmd_classify)

    inspect_parser = subparsers.add_parser("inspect", help="Print a human-readable materiality timeline.")
    inspect_parser.add_argument("--db", default="trialdiff.sqlite3")
    inspect_parser.add_argument("nct", help="NCT ID to inspect.")
    inspect_parser.add_argument("--max-paths", type=int, default=8)
    inspect_parser.set_defaults(func=cmd_inspect)

    corpus_parser = subparsers.add_parser("select-corpus", help="Select a reproducible NCT corpus.")
    corpus_parser.add_argument("--condition", default="breast cancer")
    corpus_parser.add_argument("--cutoff-date", default="2021-05-20")
    corpus_parser.add_argument("--min-versions", type=int, default=3)
    corpus_parser.add_argument("--limit", type=int, default=100)
    corpus_parser.add_argument("--page-size", type=int, default=100)
    corpus_parser.add_argument("--max-pages", type=int, default=25)
    corpus_parser.add_argument("--delay-seconds", type=float, default=0.25)
    corpus_parser.add_argument("--output-dir", default="corpora")
    corpus_parser.add_argument("--stem", help="Output filename stem without extension.")
    corpus_parser.set_defaults(func=cmd_select_corpus)

    evidence_parser = subparsers.add_parser(
        "generate-evidence",
        help="Generate citeable Evidence Records from deterministic event-class membership.",
    )
    evidence_parser.add_argument("--db", default="trialdiff.sqlite3")
    evidence_parser.add_argument("--nct", help="Optional NCT ID to generate.")
    evidence_parser.add_argument("--force", action="store_true", help="Delete existing evidence records before generating.")
    evidence_parser.add_argument("--evidence-version", type=int, default=EVIDENCE_VERSION)
    evidence_parser.set_defaults(func=cmd_generate_evidence)

    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify exported Evidence Record files against their own hashes, offline.",
    )
    verify_parser.add_argument(
        "paths",
        nargs="+",
        help="Record .json files or directories of records to verify.",
    )
    verify_parser.add_argument("--verbose", action="store_true", help="Print passing check details too.")
    verify_parser.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except sqlite3.Error as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
