# Data Dictionary — Evidence Record Schemas

Two record schemas exist. Machine-readable JSON Schemas live in `schemas/`
and are enforced in CI; this file is the human-readable companion.

Verification for both formats: `trialdiff verify <file-or-directory>`
(offline, stdlib only).

## `trialdiff.evidence_record` — current format

Used by `event_class_records_v0.1.1/records/*.json` (and all future
packages). **The file bytes are the canonical serialization**: key-sorted,
compact separators, ASCII-escaped JSON. `sha256(file bytes)` is the record's
citable hash (stored as `canonical_hash` in databases and in package
manifests).

| Field | Type | Meaning |
| --- | --- | --- |
| `schema` | string | Always `"trialdiff.evidence_record"` |
| `evidence_version` | int | Evidence generation scheme version (currently 1) |
| `event_id` | string | `evt_{nct}_v{from}_v{to}_{digest12}`; digest is derived from nct/versions/patch_hash/category/changed_paths/event_classes/rule_set_hash/evidence_version — re-derivable, see `trialdiff/evidence.py::build_event_id` |
| `trial.nct_id` | string | ClinicalTrials.gov identifier |
| `trial.clinicaltrials_gov_url` | string | Public study page |
| `versions.from_version` / `to_version` | int | Adjacent registry version pair |
| `versions.submitted_date` | string\|null | Registry submit date of the TO version |
| `classification.severity` / `severity_pre_timing` | string | Deterministic triage tier (uncalibrated); equal to each other since v0.2.1 disabled timing escalation |
| `classification.triage_label` | string | Alias of `severity` under the primitive's terminology |
| `classification.calibration_status` | string | `"uncalibrated"` — the v0.2/v0.2.1 calibration failed its gate |
| `classification.category` / `categories` | string / string[] | Highest-priority review category and the full set |
| `classification.event_classes` | string[] | Sorted deterministic factual class memberships (the current citation criterion; see `trialdiff/event_classes.py`) |
| `classification.timing_context` | string\|null | pre/early/late/post recruitment at the FROM version |
| `classification.deterministic_rules` | string[] | Rule keys that fired |
| `classification.value_signals` | object[] | Value-derived signals (timeline deltas, enrollment changes, whyStopped emptiness…) |
| `classification.rule_set_hash` | string | Combined hash: event-class rule set + triage rule component |
| `classification.event_class_rule_set_hash` | string | Hash of the event-class version, prose definitions, and normalized executable source digest |
| `classification.triage_rule_set_hash` | string | Hash of the active DB rule-table rows plus normalized executable source for value signals, suppression, path matching, timing, and patch handling |
| `changed_paths` | string[] | Sorted JSON Pointer paths changed by the patch |
| `patch` | object[] | The registry's own JSON Patch between the two versions (replayable) |
| `provenance.patch_hash` | string | `sha256(canonical_json(patch))` — re-derivable from `patch` |
| `provenance.patch_source` / `patch_source_url` | string | Where the patch came from (CT.gov internal history endpoint) |
| `provenance.patch_raw_hash` | string | Hash of the raw fetched payload |
| `provenance.from_snapshot_hash` / `to_snapshot_hash` | string\|null | Hashes of stored version snapshots; null = snapshot not stored (see `ERRATA.md` E1 for why this distinction matters) |
| `provenance.materiality_event_hash` | string | Hash of the deterministic content of the upstream materiality event (excludes wall-clock fields since E2) |
| `claims_supported` | string[] | Exactly what this record asserts |
| `claims_not_supported` | string[] | Exactly what it refuses to assert (misconduct, intent, compliance…) |
| `review_question` | string | The bounded question a human reviewer should ask |
| `citation_text` | string | Ready-made citation sentence |

## `trialdiff.alpha_demo_record` — frozen v0.1-alpha format

Used only by the 40 files in `records/`. A wrapper: richer study metadata
plus an embedded `canonical_evidence_record` whose canonical-JSON hash is
pinned as `provenance.evidence_canonical_hash`.

Differences from the current format:

| Aspect | alpha_demo_record | evidence_record |
| --- | --- | --- |
| Top-level extras | `demo_version`, `study` (9 fields incl. titles/sponsor), `live_urls`, `source_corpus`, `canonical_evidence_record` | — (`trial` carries only nct_id + URL) |
| Canonical form | The *embedded* `canonical_evidence_record`, hashed as `provenance.evidence_canonical_hash` | The file itself |
| `event_classes` / `triage_label` / `calibration_status` | absent (predates the primitive's final field set) | present |
| `event_id` derivation | v0.1-alpha scheme (digest payload without `event_classes`) — not re-derivable by current code; integrity carried by the canonical hash | current scheme, re-derivable |
| Timing escalation | active in this generation (7/40 records have `severity != severity_pre_timing`) | disabled (fields always equal) |

`EVIDENCE_RECORD_SCHEMA.md` is the original prose description of the alpha
format and is retained for the frozen package; `schemas/` holds the
machine-readable versions of both formats.

## Databases

The SQLite working database and the Postgres deployment share one logical
schema (`trialdiff/migrations/` and `postgres/migrations/` respectively).
`evidence_records.canonical_json` stores the exact canonical text
(Postgres: `text` since migration 006 — a `jsonb` column would destroy the
bytes that hash to `canonical_hash`).
