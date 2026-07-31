# TrialDiff Event-Class Evidence Records v0.1.2

This package is a separate event-class Evidence Record export. It does not modify the
frozen TrialDiff v0.1-alpha `records/` package or its manifest.

## Source

- Corpus identifier: `breast-cancer-phase2-3-limit100-v021`
- Working database: `<db_path>` (the regenerated 100-study SQLite database
  for the corpus above)
- Generation command:

```bash
python3 -m trialdiff.cli generate-evidence --db <db_path> --force
```

- Export command:

```bash
python3 scripts/export_event_class_package.py --db <db_path> --out <package_dir> \
  --corpus-label breast-cancer-phase2-3-limit100-v021 --package-version v0.1.2 --doc <source_for_DETERMINISM_ATTESTATION.md> --doc <source_for_ERRATA.md> --doc <source_for_EVIDENCE_RECORD_PRIMITIVE.md> --doc <source_for_SEVERITY_CALIBRATION_v0.2.1.md> --doc <source_for_SEVERITY_DECOUPLING_v0.2.1.md> --force
```

- Validation command:

```bash
python3 scripts/validate_event_class_package.py --package <package_dir> --db <db_path>
```

## Rule Sets

- Event-class rule set hash(es): `07957f8b90549d4f42387f51b471ecde9901b6db63bbc27b84c73631603407c0`
- Combined rule set hash(es): `318445b9ad266f51fd10ef378645c753ba7a098e3e4395c3c457750dc5f88d86`
- Triage rule set hash(es): `af5e5835e00a5fcfe2a17fd02b5fc244c2564104f93f78a1d77d7889f12a178b`
- Triage labels are uncalibrated metadata, not validated review-priority findings.
- The combined rule-set hash is the hash of the event-class rule set plus the
  triage-rule component available for that patch. Records without a prior
  materiality event use an empty triage component.

Combined hash counts:

- `318445b9ad266f51fd10ef378645c753ba7a098e3e4395c3c457750dc5f88d86`: 97 records; triage component(s): af5e5835e00a5fcfe2a17fd02b5fc244c2564104f93f78a1d77d7889f12a178b

## Counts

- Records: 97
- Trials represented: 54
- Event-class memberships: 106

Event-class counts:

- `enrollment_changed_to_zero`: 3
- `outcome_edit_cooccurs_with_results_posting`: 80
- `primary_endpoint_changed_after_primary_completion_without_results_reconciliation`: 10
- `secondary_outcome_removed_after_primary_completion`: 9
- `why_stopped_removed_in_terminal_context`: 4

Overlap counts:

- 1 class(es): 88
- 2 class(es): 9

## Export Integrity Checks

- Export writes each record as the exact canonical JSON bytes stored in
  `evidence_records.canonical_json`.
- For every exported record, the file SHA-256 equals the stored
  `evidence_records.canonical_hash`.
- `MANIFEST.sha256` covers every package file except the manifest itself.
- This export does not, by itself, attest independent regeneration or
  byte-identical re-export. Any such release claim requires separately recorded,
  manifest-attested evidence produced by the operator procedure in `RELEASING.md`.

## Supporting Documents

- `docs/DETERMINISM_ATTESTATION.md`
- `docs/ERRATA.md`
- `docs/EVIDENCE_RECORD_PRIMITIVE.md`
- `docs/SEVERITY_CALIBRATION_v0.2.1.md`
- `docs/SEVERITY_DECOUPLING_v0.2.1.md`

## Multi-Class Worked Record

- Event ID: `evt_NCT05415215_v29_v30_597faa0b4362`
- NCT ID: `NCT05415215`
- Versions: v29->v30
- Canonical hash: `6668d8199453ee4aff44a2754279c8a150c002cc3f07aadf54919057c206a08a`
- Event classes: `outcome_edit_cooccurs_with_results_posting, secondary_outcome_removed_after_primary_completion`

The reconciliation class is a co-occurrence tag, not a claim that the amendment
was harmless or purely administrative.

## Availability Status

This package is frozen in-repository for reproducibility. A repository-independent
deposit and DOI remain TODO.
