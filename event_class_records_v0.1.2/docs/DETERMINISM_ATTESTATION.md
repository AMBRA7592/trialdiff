# TrialDiff v0.1.2 Determinism Attestation

Date: 2026-07-31

This attestation records the controlled dual regeneration used to freeze the
TrialDiff event-class Evidence Record package v0.1.2. The two runs started from
independent byte-identical copies of the same frozen SQLite input and used the
same release code tree. No production database or published artifact was
modified during this procedure.

## Release inputs

- Source database: `trialdiff_breast_cancer_limit100_v021.sqlite3`
- Source database size: `832503808` bytes
- Source database SHA-256:
  `02138437b57e20c6c8c0fbf48347df0adde5868172077669345141d4b91a5e6c`
- SQLite integrity check: `ok`
- Source counts: 100 trials; 4,485 trial patches
- Release branch commit:
  `6176b2121bdcd1cac6ce859d7749ab188de4b183`
- Release tree:
  `6ab53fdde75d4273bf728630f862fee6072f9daa`
- Python: `3.14.2`
- SQLite: `3.43.2`

The source database was not regenerated or written in place. Two temporary
copies, A and B, were made before classification. Each copy had the same
SHA-256 as the source database before either run began.

## Rule-set identities

- Event-class rule-set hash:
  `07957f8b90549d4f42387f51b471ecde9901b6db63bbc27b84c73631603407c0`
- Triage rule-set hash:
  `af5e5835e00a5fcfe2a17fd02b5fc244c2564104f93f78a1d77d7889f12a178b`
- Combined rule-set hash:
  `318445b9ad266f51fd10ef378645c753ba7a098e3e4395c3c457750dc5f88d86`

## Independent regeneration

The following commands were run separately against copy A and copy B:

```text
python3 -m trialdiff.cli classify --db <copy>.sqlite3 --force
python3 -m trialdiff.cli generate-evidence --db <copy>.sqlite3 --force
```

Each run reported:

```text
deleted_existing_events=868
classified=868  skipped_missing_from_record=0
generated=97  skipped_existing=0  deleted_existing=100
```

For each regenerated database, the ordered list of
`event_id<TAB>canonical_hash` values was exported. The two lists had an empty
unified diff and shared this SHA-256:

`e3078487c9cb286a53555f0a15dd23b7f0e968d66e006d5e5e797f6cf73ac5f2`

## Mechanical boundary analysis

The boundary analyzer was run independently against both regenerated copies.
Both runs returned:

```text
patches=4485
missing_from_record=0
inclusive_primary_after_completion=73
results_cooccurring=63
clean=10
```

The partition invariant held: `73 = 63 + 10`.

## Corrected population

Both regenerated databases returned the same corrected population:

- Evidence Records: 97
- Represented trials: 54
- Event-class memberships: 106
- `primary_endpoint_changed_after_primary_completion_without_results_reconciliation`: 10
- `secondary_outcome_removed_after_primary_completion`: 9
- `enrollment_changed_to_zero`: 3
- `why_stopped_removed_in_terminal_context`: 4
- `outcome_edit_cooccurs_with_results_posting`: 80
- Records with one class: 88
- Records with two classes: 9
- Records with three classes: 0

These results satisfy the v0.1.2 freeze gates. Package export and package-level
validation remain separate checks and are recorded by the package manifest and
`VALIDATION.md`.
