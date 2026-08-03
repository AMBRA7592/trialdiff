# TrialDiff v0.1.3 Determinism Attestation

Date: 2026-08-03

This attestation records the controlled dual regeneration used to prepare the
TrialDiff event-class Evidence Record package v0.1.3. The two runs started from
independent byte-identical copies of the accepted v0.1.2 SQLite A artifact and
used the same merged release code tree. No production database or published
artifact was modified during this procedure.

## Release Inputs

- Accepted source database: durable v0.1.2 release artifact `a.sqlite3`
- Source database size: `832503808` bytes
- Source database SHA-256:
  `8105dbad8ec65a83fa8304b17b193e71a69bef0a0e38c935fd3299cc182e1238`
- SQLite integrity check: `ok`
- Source counts: 100 trials; 4,485 trial patches
- Release commit:
  `7a15a1fd1aa7c9c75dc3dcf96a40be70dd7831bb`
- Release tree:
  `29e42732f4bf8b5cbb4244fa849f5dc5ac44726e`
- Python: `3.14.2`
- SQLite: `3.43.2`

The accepted source database was not written in place. Copies A and B were
created before classification. Each copy had the accepted source SHA-256 above
before either regeneration began.

## Pre-Regeneration Input Audit

The private-corpus stop gate was run before either copy was classified:

```text
python3 scripts/audit_event_class_inputs.py \
  --db <accepted-v0.1.2-a.sqlite3> --expect-v0.3
```

Complete output:

```json
{
  "classified_records": 97,
  "classified_trials": 54,
  "corrected_secondary_memberships": 12,
  "event_class_counts": {
    "enrollment_changed_to_zero": 3,
    "outcome_edit_cooccurs_with_results_posting": 80,
    "primary_endpoint_changed_after_primary_completion_without_results_reconciliation": 10,
    "secondary_outcome_removed_after_primary_completion": 12,
    "why_stopped_removed_in_terminal_context": 4
  },
  "event_class_memberships": 109,
  "event_class_overlap_counts": {
    "1": 85,
    "2": 12
  },
  "historical_v02_secondary_memberships": 9,
  "operations": {
    "add": 25076,
    "remove": 22710,
    "replace": 99332
  },
  "patches": 4485,
  "postcompletion_secondary_count_decreases": 11,
  "primary_after_completion": 73,
  "primary_clean": 10,
  "primary_literal_vs_state_disagreements": [],
  "primary_relevant_patches": 148,
  "primary_results_cooccurring": 63,
  "reconstructed_to_records": 100,
  "secondary_candidates": 16,
  "secondary_count_decreases_without_structural_candidate": [],
  "secondary_whole_item_replace_operations": 0,
  "stored_to_records": 4385,
  "v02_vs_corrected_secondary_disagreements": [
    "NCT01224678_v109_v110",
    "NCT03094169_v11_v12",
    "NCT03734029_v29_v30"
  ]
}
```

The 4,385 exact stored-TO versus patch-replay comparisons prove internal
consistency between two products of the same ingestion. They do not prove
independent fidelity to the source registry. The 100 missing-TO records replayed
without error; their reconstruction is inferred from the 4,385 exact
comparisons and was not externally checked against registry snapshots.

## Rule-Set Identities

- Event-class rule-set hash:
  `74a6f55a686c29aa023171acd6b43f27ea95f2b0af2d49094ac70287ba4e502c`
- Triage rule-set hash:
  `af5e5835e00a5fcfe2a17fd02b5fc244c2564104f93f78a1d77d7889f12a178b`
- Combined rule-set hash:
  `fc87f4f0a74bc789dbe4ba85893c2c96f55db62c22970be4e991288104291621`

## Independent Regeneration

Copies A and B were regenerated in separate processes with different hash
seeds. Each process ran:

```text
python3 -m trialdiff.cli classify --db <copy>.sqlite3 --force
python3 -m trialdiff.cli generate-evidence --db <copy>.sqlite3 --force
```

Each run reported:

```text
deleted_existing_events=868
classified=868  skipped_missing_from_record=0
generated=97  skipped_existing=0  deleted_existing=97
```

For each regenerated database, the ordered list of
`event_id<two spaces>canonical_hash` values was exported. The two 97-line lists
had an empty unified diff and shared this SHA-256:

`f6920e2f5d8afa7caef18d9d102beafb1d56a89d469a1c19a4d3a82b1213da2b`

## Mechanical Boundary Analysis

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

## Corrected Population

Both regenerated databases returned the same corrected population:

- Evidence Records: 97
- Represented trials: 54
- Event-class memberships: 109
- `primary_endpoint_changed_after_primary_completion_without_results_reconciliation`: 10
- `secondary_outcome_removed_after_primary_completion`: 12
- `enrollment_changed_to_zero`: 3
- `why_stopped_removed_in_terminal_context`: 4
- `outcome_edit_cooccurs_with_results_posting`: 80
- Records with one class: 85
- Records with two classes: 12
- Records with three classes: 0

These results satisfy the v0.1.3 regeneration gates. Package export,
byte-identical package comparison, package validation, and offline record
verification remain separate stop gates.
