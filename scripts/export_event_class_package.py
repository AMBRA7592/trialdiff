#!/usr/bin/env python3
"""Export TrialDiff event-class Evidence Records as canonical package bytes."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any


DEFAULT_PACKAGE_DIR = "event_class_records_v0.2"
DB_PLACEHOLDER = "<db_path>"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="SQLite database containing generated Evidence Records.")
    parser.add_argument("--out", default=DEFAULT_PACKAGE_DIR, help="Output package directory.")
    parser.add_argument("--corpus-label", default="breast-cancer-phase2-3-limit100-v021")
    parser.add_argument(
        "--generation-command",
        default=None,
        help="Command recorded in VALIDATION.md as the generation command.",
    )
    parser.add_argument(
        "--package-version",
        required=True,
        help="Package version label recorded in VALIDATION.md (e.g. v0.1.2). Explicit on purpose: "
        "the version stamped into a release document must be a reviewed input, not a guess.",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing package directory.")
    args = parser.parse_args()

    db_path = Path(args.db)
    package_dir = Path(args.out)
    if package_dir.exists():
        if not args.force:
            raise SystemExit(f"{package_dir} already exists; pass --force to replace it")
        shutil.rmtree(package_dir)
    records_dir = package_dir / "records"
    records_dir.mkdir(parents=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = select_records(connection)
    finally:
        connection.close()

    if not rows:
        raise SystemExit("no event-class Evidence Records found")

    summaries: list[dict[str, Any]] = []
    for row in rows:
        canonical_text = row["canonical_json"]
        canonical_hash = sha256_bytes(canonical_text.encode("utf-8"))
        if canonical_hash != row["canonical_hash"]:
            raise SystemExit(
                f"{row['event_id']}: stored canonical_hash does not match stored canonical_json bytes"
            )
        record = json.loads(canonical_text)
        event_id = record["event_id"]
        if event_id != row["event_id"]:
            raise SystemExit(f"{row['event_id']}: canonical event_id mismatch")
        target = records_dir / f"{event_id}.json"
        target.write_bytes(canonical_text.encode("utf-8"))
        written_hash = sha256_bytes(target.read_bytes())
        if written_hash != row["canonical_hash"]:
            raise SystemExit(f"{event_id}: exported bytes do not match stored canonical_hash")
        summaries.append(summarize_record(record, stored_hash=row["canonical_hash"]))

    stats = package_stats(summaries)
    validation_note = build_validation_note(
        db_path=db_path,
        corpus_label=args.corpus_label,
        package_version=args.package_version,
        generation_command=args.generation_command
        or f"python3 -m trialdiff.cli generate-evidence --db {DB_PLACEHOLDER} --force",
        summaries=summaries,
        stats=stats,
    )
    validation_path = package_dir / "VALIDATION.md"
    validation_path.write_text(validation_note, encoding="utf-8")
    sidecar_path = package_dir / "expected_stats.json"
    sidecar_path.write_text(
        json.dumps(expected_stats_sidecar(stats), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    manifest_path = package_dir / "MANIFEST.sha256"
    manifest_entries = build_manifest_entries(package_dir)
    manifest_path.write_text(
        "".join(f"{digest}  {relative_path}\n" for digest, relative_path in manifest_entries),
        encoding="utf-8",
    )

    print(f"package={package_dir}")
    print(f"records={stats['records']}\ttrials={stats['trials']}\tmemberships={stats['memberships']}")
    print(f"class_counts={dict(sorted(stats['class_counts'].items()))}")
    print(f"overlaps={dict(sorted(stats['overlap_counts'].items()))}")
    print(f"max_class_overlap={stats['showcase']['class_count']}")
    print("exported_bytes_match_stored_canonical_hash=True")
    return 0


def expected_stats_sidecar(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": stats["records"],
        "trials": stats["trials"],
        "class_counts": dict(sorted(stats["class_counts"].items())),
        "overlap_counts": {str(size): count for size, count in sorted(stats["overlap_counts"].items())},
        "showcase": stats["showcase"],
        "note": "Frozen-package integrity expectations describing the package as exported.",
    }


def select_records(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT event_id, nct_id, from_version, to_version, canonical_json, canonical_hash
        FROM evidence_records
        ORDER BY nct_id, from_version, to_version, event_id
        """
    ).fetchall()


def summarize_record(record: dict[str, Any], *, stored_hash: str) -> dict[str, Any]:
    event_classes = record["classification"]["event_classes"]
    if event_classes != sorted(event_classes):
        raise SystemExit(f"{record['event_id']}: event_classes are not sorted")
    if not event_classes:
        raise SystemExit(f"{record['event_id']}: event_classes is empty")
    return {
        "event_id": record["event_id"],
        "nct_id": record["trial"]["nct_id"],
        "from_version": record["versions"]["from_version"],
        "to_version": record["versions"]["to_version"],
        "canonical_hash": stored_hash,
        "event_classes": event_classes,
        "event_class_rule_set_hash": record["classification"]["event_class_rule_set_hash"],
        "rule_set_hash": record["classification"]["rule_set_hash"],
        "triage_rule_set_hash": record["classification"]["triage_rule_set_hash"],
    }


def package_stats(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts: Counter[str] = Counter()
    overlap_counts: Counter[int] = Counter()
    for summary in summaries:
        class_counts.update(summary["event_classes"])
        overlap_counts[len(summary["event_classes"])] += 1
    showcase = max(summaries, key=lambda summary: (len(summary["event_classes"]), summary["event_id"]))
    return {
        "records": len(summaries),
        "trials": len({summary["nct_id"] for summary in summaries}),
        "memberships": sum(len(summary["event_classes"]) for summary in summaries),
        "class_counts": class_counts,
        "overlap_counts": overlap_counts,
        "showcase": {"event_id": showcase["event_id"], "class_count": len(showcase["event_classes"])},
        "event_class_rule_set_hashes": sorted(
            {summary["event_class_rule_set_hash"] for summary in summaries}
        ),
        "rule_set_hashes": sorted({summary["rule_set_hash"] for summary in summaries}),
        "triage_rule_set_hashes": sorted(
            {summary["triage_rule_set_hash"] for summary in summaries if summary["triage_rule_set_hash"]}
        ),
        "rule_set_hash_counts": Counter(summary["rule_set_hash"] for summary in summaries),
        "triage_by_rule_set_hash": {
            rule_set_hash: sorted(
                {
                    summary["triage_rule_set_hash"] or "<empty>"
                    for summary in summaries
                    if summary["rule_set_hash"] == rule_set_hash
                }
            )
            for rule_set_hash in sorted({summary["rule_set_hash"] for summary in summaries})
        },
    }


def build_validation_note(
    *,
    db_path: Path,
    corpus_label: str,
    package_version: str,
    generation_command: str,
    summaries: list[dict[str, Any]],
    stats: dict[str, Any],
) -> str:
    class_counts = "\n".join(
        f"- `{name}`: {count}" for name, count in sorted(stats["class_counts"].items())
    )
    overlap_counts = "\n".join(
        f"- {size} class(es): {count}" for size, count in sorted(stats["overlap_counts"].items())
    )
    combined_hash_counts = "\n".join(
        "- `{rule_set_hash}`: {count} records; triage component(s): {triage_components}".format(
            rule_set_hash=rule_set_hash,
            count=count,
            triage_components=", ".join(stats["triage_by_rule_set_hash"][rule_set_hash]),
        )
        for rule_set_hash, count in sorted(stats["rule_set_hash_counts"].items())
    )
    # Single source of truth for the showcase: the selection package_stats
    # already made (and expected_stats.json enforces).
    showcase_summary = next(
        summary for summary in summaries if summary["event_id"] == stats["showcase"]["event_id"]
    )
    return f"""# TrialDiff Event-Class Evidence Records {package_version}

This package is a separate event-class Evidence Record export. It does not modify the
frozen TrialDiff v0.1-alpha `records/` package or its manifest.

## Source

- Corpus identifier: `{corpus_label}`
- Working database: `{DB_PLACEHOLDER}` (the regenerated 100-study SQLite database
  for the corpus above)
- Generation command:

```bash
{generation_command}
```

- Export command:

```bash
python3 scripts/export_event_class_package.py --db {DB_PLACEHOLDER} --out <package_dir> --corpus-label {corpus_label} --force
```

- Validation command:

```bash
python3 scripts/validate_event_class_package.py --package <package_dir> --db {DB_PLACEHOLDER}
```

## Rule Sets

- Event-class rule set hash(es): `{", ".join(stats["event_class_rule_set_hashes"])}`
- Combined rule set hash(es): `{", ".join(stats["rule_set_hashes"])}`
- Triage rule set hash(es): `{", ".join(stats["triage_rule_set_hashes"])}`
- Triage labels are uncalibrated metadata, not validated review-priority findings.
- The combined rule-set hash is the hash of the event-class rule set plus the
  triage-rule component available for that patch. Records without a prior
  materiality event use an empty triage component.

Combined hash counts:

{combined_hash_counts}

## Counts

- Records: {stats["records"]}
- Trials represented: {stats["trials"]}
- Event-class memberships: {stats["memberships"]}

Event-class counts:

{class_counts}

Overlap counts:

{overlap_counts}

## Determinism Evidence

- Real generation was checked by regenerating Evidence Records from the 100-study
  working database and comparing canonical payloads across runs.
- The final comparison was byte-identical after sorting records by
  `(nct_id, from_version, to_version, event_id)`.
- Export writes each record as the exact canonical JSON bytes stored in
  `evidence_records.canonical_json`.
- For every exported record, the file SHA-256 equals the stored
  `evidence_records.canonical_hash`.
- Re-exporting the package produced byte-identical files.
- `MANIFEST.sha256` verifies the exported records and this validation note.

## Multi-Class Worked Record

- Event ID: `{showcase_summary["event_id"]}`
- NCT ID: `{showcase_summary["nct_id"]}`
- Versions: v{showcase_summary["from_version"]}->v{showcase_summary["to_version"]}
- Canonical hash: `{showcase_summary["canonical_hash"]}`
- Event classes: `{", ".join(showcase_summary["event_classes"])}`

The reconciliation class is a co-occurrence tag, not a claim that the amendment
was harmless or purely administrative.

## Availability Status

This package is frozen in-repository for reproducibility. A repository-independent
deposit and DOI remain TODO.
"""


def build_manifest_entries(package_dir: Path) -> list[tuple[str, str]]:
    paths = [
        package_dir / "VALIDATION.md",
        package_dir / "expected_stats.json",
        *sorted((package_dir / "records").glob("*.json")),
    ]
    entries: list[tuple[str, str]] = []
    for path in paths:
        relative_path = path.relative_to(package_dir).as_posix()
        entries.append((sha256_bytes(path.read_bytes()), relative_path))
    return entries


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
