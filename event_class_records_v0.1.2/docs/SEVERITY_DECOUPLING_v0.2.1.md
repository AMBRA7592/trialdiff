# Severity Decoupling v0.2.1

Status: severity decoupled from validated review-priority claims; Evidence Records remain supported.

## Decision

TrialDiff severity remains a deterministic, reproducible triage label. It is not a validated review-priority standard and must not be presented as one in public copy, schema descriptions, or UI surfaces.

The buyer-facing high-priority brief remains blocked. The citable Evidence Record primitive remains intact.

## Finding Behind The Decision

The v0.2.1 re-certification failed the critical-tier gate on fresh records. The gate required at least 24 of 30 TrialDiff-critical records to be independently confirmed as critical. Across fresh independent applications of the rubric, critical confirmations were 4/30, 5/30, 12/30, and 17/30.

That spread is the substantive finding. It shows that the critical review-priority boundary was not stable enough to serve as a validated reference standard in this design. A third tuning cycle would risk optimizing against an unstable target rather than certifying a real standard.

## What Survives

The following claims remain supported:

- TrialDiff converts public ClinicalTrials.gov amendment history into source-linked Evidence Records.
- Evidence IDs, canonical JSON, source hashes, changed paths, deterministic rules, provenance, and claim boundaries are inspectable and reproducible.
- Frozen v0.1-alpha records remain byte-identical and verifiable against `MANIFEST.sha256`.
- Severity values can still be used as deterministic triage metadata for sorting and inspection.

## What Is Forfeited

The following claims are not supported:

- that `critical` means independently validated critical review priority;
- that `high` or `critical` labels are calibrated for external buyer-facing prioritization;
- that the current severity rubric is a stable independent reference standard;
- that severity labels should be cited as validated judgments rather than deterministic triage metadata.

## Provenance Constraint

Do not mutate frozen `records/*.json` to rename or rewrite existing severity fields. Those files are hash-pinned. Editing them would break `MANIFEST.sha256` and damage the provenance guarantee the project is meant to preserve.

The decoupling is interpretive and surface-level for existing records: documentation, schema text, and frontend labels define severity as uncalibrated triage metadata. Future regenerated records may add an explicit field such as `calibration_status: uncalibrated`, but historical frozen records stay byte-identical.
