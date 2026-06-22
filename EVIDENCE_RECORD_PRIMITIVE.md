# Evidence Record — Primitive Specification

Status: specification (v0.1)
Date: 2026-06-19
Scope: defines the Evidence Record primitive. TrialDiff is the reference implementation.

## Definition

An Evidence Record is a deterministic, claim-bounded object that asserts a bounded public-record change event, addressable by a stable identifier and independently verifiable from its cited source.

## Fields

- `record_id` — stable identifier, deterministically derived from the record's content. Serves as the citation key; identical inputs always yield the same id.
- `source` — for each cited source: retrieval URL, content hash at the observed version, and version reference(s) (e.g. from/to).
- `change` — canonical representation of what changed: the changed paths and their before/after values.
- `ruleset_hash` — hash of the logic version that produced any derived fields. A logic change yields a new `ruleset_hash`, never a silent edit to existing records.
- `event_classes` — deterministic set of factual class memberships for the bounded change event. A record is one-per-source-change and can carry multiple classes; class membership is not a priority ranking. The primitive permits an empty class set; TrialDiff's current reference implementation emits only records with at least one event class.
- `triage_label` — deterministic classification of the change. Uncalibrated: a reproducible heuristic, not a validated priority.
- `calibration_status` — status of any external validation for `triage_label`, e.g. `uncalibrated`.
- `claims_supported` — explicit list of what the record asserts.
- `claims_not_supported` — explicit list of what the record does not assert.
- `record_hash` — hash of the record's canonical JSON form.
- `generated_at`, generator/version metadata.

## Determinism guarantee

A record is a pure function of cited source content, source-selection rules, canonicalization rules, generator version, and `ruleset_hash`. The same inputs produce byte-identical canonical JSON, and therefore an identical `record_hash` and `record_id`. Canonicalization — stable key ordering and fixed normalization — is what makes the hash reproducible. Regenerating a record from the same inputs is a verification, not a re-derivation.

## Provenance and hash rules

- Each source is pinned by content hash at the observed version; the record is derivable from those sources alone.
- The record's own canonical form is hashed as `record_hash`.
- Published records are immutable. A logic change produces new records under a new `ruleset_hash`; it never mutates the bytes of an existing record, which would break its hash and any citation to it.
- Verification: retrieve each cited or archived source payload → confirm its content hash → recompute the canonical form → confirm `record_hash`.

## Claim-boundary rule

Every record states `claims_supported` and `claims_not_supported`. A record asserts only the structural fact of the change as represented in its cited source. It does not assert intent, wrongdoing, regulatory compliance, disclosure status in any other venue, or substantive significance. `triage_label` is uncalibrated and is explicitly neither a validated priority nor a finding.

## Worked instance: TrialDiff

TrialDiff is the reference implementation. It produces Evidence Records for ClinicalTrials.gov protocol-amendment changes: deterministic event ids of the form `evt_{nct_id}_v{from}_v{to}_{hash}`, canonical JSON, source URLs and content hashes, explicit claim boundaries, deterministic `event_classes`, and a `triage_label` (formerly `severity`). That label's calibration was attempted under blinded review and did not pass the pre-registered gate; it is retained as uncalibrated metadata (see `SEVERITY_CALIBRATION_v0.2.1.md` and `SEVERITY_DECOUPLING_v0.2.1.md`).

## Other instantiations

The same primitive applies wherever a change in a public record must be cited and independently verified — for example regulatory filings or revisions to public datasets — without extending this specification to those domains.
