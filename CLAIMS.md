# Claims

TrialDiff Evidence Demo v0.1-alpha supports the following bounded claims.

## Core Claim

TrialDiff can take public ClinicalTrials.gov record changes and produce auditable, replayable Evidence Records that make meaningful amendments easier to inspect.

## Supported Claims

- The demo uses a bounded 25-study breast-cancer-related corpus.
- TrialDiff stores adjacent ClinicalTrials.gov record-version patches.
- TrialDiff classifies selected high-signal amendments using deterministic rules and value signals.
- TrialDiff assigns severity as deterministic, reproducible, uncalibrated triage metadata, not as validated review priority or a finding of wrongdoing.
- TrialDiff generates stable Evidence Record IDs from source data, patch hashes, changed paths, rule-set hash, category, and evidence version.
- TrialDiff stores and exports hash/provenance fields for patches, snapshots, materiality events, and generated Evidence Records.
- The frozen package contains 40 selected Evidence Records carrying high or critical triage labels.
- Each exported record includes NCT ID, study title, sponsor, source links, version references, changed paths, JSON Patch data, rules/value signals, timing context, category, severity, provenance fields, supported claims, non-claims, and live demo URLs.
- The exported records can be validated against `MANIFEST.sha256`.

## What The Demo Proves

The demo proves that a conservative, deterministic evidence layer can be built over ClinicalTrials.gov amendment history.

It does not prove that any specific amendment was improper, clinically meaningful, undisclosed in publications, or made with bad intent.

## Severity Calibration Status

The v0.2/v0.2.1 calibration did not validate severity as an external review-priority standard. Against the pre-registered gate of at least 24/30 critical confirmations, the observed confirmations were 6/30 and 3/30 (v0.2 reviewers), 17/30 and 4/30 (v0.2.1 re-certification reviewers), and 4/30, 5/30, 12/30, 17/30 across the v0.2.1 critical-stratum fresh applications. Severity therefore remains an uncalibrated triage label. See `SEVERITY_CALIBRATION_v0.2.md`, `SEVERITY_CALIBRATION_v0.2.1.md`, and `SEVERITY_DECOUPLING_v0.2.1.md`.
