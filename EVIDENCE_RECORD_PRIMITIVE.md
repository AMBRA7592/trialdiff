# Evidence Record — Primitive Specification

Status: specification (v0.2; source-closure clarification)
Date: 2026-08-03
Scope: defines the Evidence Record primitive. TrialDiff is the reference implementation.

## Definition

An Evidence Record is a deterministic, claim-bounded object that asserts a
bounded public-record change event and is addressable by a stable identifier.
Its canonical bytes and provenance anchors are independently integrity-verifiable.
Independent recomputation of derived claims additionally requires a
source-closed record that carries every source field consumed by its rules.

## Fields

- `record_id` — stable identifier, deterministically derived from the record's content. Serves as the citation key; identical inputs always yield the same id.
- `source` — for each cited source: retrieval URL, content hash at the observed version, and version reference(s) (e.g. from/to).
- `change` — canonical representation of what changed: the changed paths and their before/after values.
- `ruleset_hash` — hash of the logic version that produced any derived fields. In TrialDiff this includes normalized implementation-source bytes as well as declarative definitions/rule rows. A logic change yields a new `ruleset_hash`, never a silent edit to existing records.
- `event_classes` — deterministic set of factual class memberships for the bounded change event. A record is one-per-source-change and can carry multiple classes; class membership is not a priority ranking. The primitive permits an empty class set; TrialDiff's current reference implementation emits only records with at least one event class.
- `triage_label` — deterministic classification of the change. Uncalibrated: a reproducible heuristic, not a validated priority.
- `calibration_status` — status of any external validation for `triage_label`, e.g. `uncalibrated`.
- `claims_supported` — explicit list of what the record asserts.
- `claims_not_supported` — explicit list of what the record does not assert.
- `record_hash` — hash of the record's canonical JSON form.
- `generated_at`, generator/version metadata.

## Determinism guarantee

A record is a pure function of cited source content, source-selection rules,
canonicalization rules, generator version, and `ruleset_hash`. The same inputs
produce byte-identical canonical JSON, and therefore an identical `record_hash`
and `record_id`. Canonicalization -- stable key ordering and fixed normalization
-- is what makes the hash reproducible. This guarantee does not imply that the
record itself contains every input needed for clean-room recomputation.

## Integrity is not correctness

The hash chain proves byte integrity: a record, once published, is
verifiably unaltered, and any citation to it stays stable. It does not
prove semantic correctness: a record can verify perfectly and still carry
a derived claim that its own cited source contradicts, if the generating
logic was defective. Correctness is governed by the `ruleset_hash`
discipline (defective logic is corrected in a NEW generation under a new
hash) and by a published errata record; verification tooling must not be
described as validating claims. See `ERRATA.md` for the operative example.

## Provenance, source closure, and hash rules

- Each cited source version is pinned by content hash.
- A source-closed record also carries, or points immutably to, every source
  field consumed by its predicates. A hash without the corresponding bytes is
  an identity anchor, not a reconstructible source.
- The record's own canonical form is hashed as `record_hash`.
- Published records are immutable. A logic change produces new records under a new `ruleset_hash`; it never mutates the bytes of an existing record, which would break its hash and any citation to it.
- Integrity verification: confirm canonical form and `record_hash`, then compare
  the record against its package manifest or deployed database hash.
- Predicate reconstruction: obtain the immutable source bytes or source slices,
  confirm their hashes, and recompute the predicates with an independent
  implementation. This stronger step is unavailable when required source bytes
  are not published.

## Claim-boundary rule

Every record states `claims_supported` and `claims_not_supported`. A record asserts only the structural fact of the change as represented in its cited source. It does not assert intent, wrongdoing, regulatory compliance, disclosure status in any other venue, or substantive significance. `triage_label` is uncalibrated and is explicitly neither a validated priority nor a finding.

## Worked instance: TrialDiff

TrialDiff is the reference implementation. It produces Evidence Records for
ClinicalTrials.gov protocol-amendment changes: deterministic event ids of the
form `evt_{nct_id}_v{from}_v{to}_{hash}`, canonical JSON, source URLs and
content hashes, explicit claim boundaries, deterministic `event_classes`, and
a `triage_label` (formerly `severity`). That label's calibration was attempted
under blinded review and did not pass the pre-registered gate; it is retained
as uncalibrated metadata (see `SEVERITY_CALIBRATION_v0.2.1.md` and
`SEVERITY_DECOUPLING_v0.2.1.md`).

The published TrialDiff v0.1.2 event-class package is integrity-verifiable but
not fully source-closed: its records carry patches and snapshot hashes, but not
every snapshot slice consumed by four of the five predicates. It therefore does
not support clean-room recomputation of every membership from packaged bytes
alone. See `CLAIMS.md`, `NON_CLAIMS.md`, and `ERRATA.md` E4.

## Other instantiations

The same primitive applies wherever a change in a public record must be cited and independently verified — for example regulatory filings or revisions to public datasets — without extending this specification to those domains.
