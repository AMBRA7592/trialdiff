# TrialDiff Event-Class Evidence Records v0.1.1

This package is a separate event-class Evidence Record export. It does not modify the
frozen TrialDiff v0.1-alpha `records/` package or its manifest.

This v0.1.1 package is a validation-note update to v0.1. The canonical record
payloads are unchanged; this note adds the boundary-analysis counts used by the
paper.

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
python3 scripts/export_event_class_package.py --db <db_path> --out <package_dir> --corpus-label breast-cancer-phase2-3-limit100-v021 --force
```

- Validation command:

```bash
python3 scripts/validate_event_class_package.py --package <package_dir> --db <db_path>
```

## Rule Sets

- Event-class rule set hash(es): `a6734d37c1adc34c5c3b770ec40fbedcf8e8e2fa4bc9d56d4eab55d2e5867c4e`
- Combined rule set hash(es): `d789a605fe5bcdf98a6703791c1db7d9c6d332fc039293c5d0ee253ef3d10d60, fda3c8331ce1074d3566d02a035a60d1b422f1bfcfac8798072414cccaf3f8a2`
- Triage rule set hash(es): `6fc6d7533e740cc38ca0ba0425927ade66f2f90b067963c5cf52d08a88f8d883`
- Triage labels are uncalibrated metadata, not validated review-priority findings.
- The combined rule-set hash is the hash of the event-class rule set plus the
  triage-rule component available for that patch. Records without a prior
  materiality event use an empty triage component.

Combined hash counts:

- `d789a605fe5bcdf98a6703791c1db7d9c6d332fc039293c5d0ee253ef3d10d60`: 3 records; triage component(s): <empty>
- `fda3c8331ce1074d3566d02a035a60d1b422f1bfcfac8798072414cccaf3f8a2`: 97 records; triage component(s): 6fc6d7533e740cc38ca0ba0425927ade66f2f90b067963c5cf52d08a88f8d883

## Counts

- Records: 100
- Trials represented: 52
- Event-class memberships: 113

Event-class counts:

- `enrollment_changed_to_zero`: 1
- `outcome_edit_cooccurs_with_results_posting`: 80
- `primary_endpoint_changed_after_primary_completion_without_results_reconciliation`: 10
- `secondary_outcome_removed_after_primary_completion`: 9
- `why_stopped_removed_in_terminal_context`: 13

Overlap counts:

- 1 class(es): 88
- 2 class(es): 11
- 3 class(es): 1

## Boundary Analysis

The headline reconciliation analysis is computed over all adjacent-version
patches in the `breast-cancer-phase2-3-limit100-v021` working database.

- Adjacent-version patches scanned: 4,485
- Inclusive primary-endpoint-after-primary-completion flag: 73 patches
- Inclusive flagged patches co-occurring with results posting: 63 patches
- Clean primary endpoint changed after primary completion without results
  reconciliation: 10 patches

The 63 co-occurring patches are reconciliation-confounded: the package records
only co-occurrence with a results signal, not harmlessness or administrative
status. The 10 clean patches are the members of
`primary_endpoint_changed_after_primary_completion_without_results_reconciliation`.

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

- Event ID: `evt_NCT04278144_v33_v34_bdd9f29ed71e`
- NCT ID: `NCT04278144`
- Versions: v33->v34
- Canonical hash: `e160c1c85806e768f64a8b6cbf27c42fb00f847acd2c4b1b68e59583a3e3cb6a`
- Event classes: `outcome_edit_cooccurs_with_results_posting, secondary_outcome_removed_after_primary_completion, why_stopped_removed_in_terminal_context`

The reconciliation class is a co-occurrence tag, not a claim that the amendment
was harmless or purely administrative.

## Availability Status

This package is frozen in-repository for reproducibility and prepared for
repository-independent deposit.
