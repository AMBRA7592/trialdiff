# Claims

This file defines the current bounded claims for TrialDiff's frozen packages,
event-class generator, and live evidence layer. Package-specific counts remain
claims of the named immutable package, subject to `ERRATA.md`.

## Core claim

TrialDiff can convert public ClinicalTrials.gov record-version changes into
deterministic, source-linked Evidence Records with replayable patches, explicit
event-class definitions, content hashes, and bounded supported/non-supported
claims.

## Supported claims

- TrialDiff stores adjacent ClinicalTrials.gov record-version patches and
  applies deterministic event-class predicates to a named, frozen corpus.
- Within an event-class package, the exported membership set is intended to be
  exhaustive for that frozen corpus, generator version, and rule-set hash. A
  missed membership is therefore an erratum, not an undocumented selection.
- Event IDs, canonical record bytes, and manifests make a published generation
  immutable and make later rule changes visible through rotated hashes and IDs.
- `trialdiff verify` checks canonical form and internal hash consistency;
  package manifests and deployed database hashes anchor artifact authenticity.
- The live v0.1.2 layer and Zenodo v0.1.2 package contain 97 records over 54
  trials and 106 event-class memberships. They remain exact v0.1.2 release
  bytes and carry erratum E4.
- The separately frozen, not-yet-published v0.1.3 package contains 97 records
  over 54 trials and 109 event-class memberships under the v0.3 predicates. It
  corrects E4 but is not claimed to be live or DOI-deposited until those
  owner-gated release steps occur.
- The frozen v0.1-alpha package contains 40 selected Evidence Records from a
  bounded 25-study corpus. Its selection rule is not an exhaustive event-class
  export.
- Severity is deterministic, reproducible, uncalibrated triage metadata. It is
  not validated review priority or a finding of wrongdoing.

## Verification levels

TrialDiff currently supports two distinct forms of checking:

1. **Byte integrity and authenticity:** canonical hashes, manifests, database
   hashes, and exact HTTP response bytes identify the artifact that was frozen.
2. **Generator correctness over the private frozen input:** regression tests,
   full-corpus audits, dual regeneration, and halt-on-divergence release gates
   test the implementation against the retained source database.

The v0.1.2 and v0.1.3 records are not fully source-closed: they include the
adjacent-version patch and snapshot hashes, but not every registry snapshot
slice required to independently recompute all five predicates. Full clean-room
predicate reconstruction from packaged bytes alone is therefore not claimed.

## Severity calibration status

The v0.2/v0.2.1 calibration did not validate severity as an external
review-priority standard. Against the pre-registered gate of at least 24/30
critical confirmations, the observed confirmations were 6/30 and 3/30 (v0.2
reviewers), 17/30 and 4/30 (v0.2.1 re-certification reviewers), and 4/30, 5/30,
12/30, 17/30 across the v0.2.1 critical-stratum fresh applications. Severity
therefore remains an uncalibrated triage label. See
`SEVERITY_CALIBRATION_v0.2.md`, `SEVERITY_CALIBRATION_v0.2.1.md`, and
`SEVERITY_DECOUPLING_v0.2.1.md`.
