# TrialDiff v0.1-alpha Release Note

Date: 2026-06-17

TrialDiff v0.1-alpha is a bounded Evidence Demo, not a product launch. It demonstrates that public ClinicalTrials.gov record changes can be converted into deterministic, source-linked Evidence Records with explicit claims, non-claims, provenance fields, rule attribution, and canonical JSON.

Severity is deterministic, reproducible, uncalibrated triage metadata. It is not validated review priority and not proven wrongdoing.

## What Exists

- Live demo: https://trialdiff.vercel.app
- Repository: https://github.com/AMBRA7592/trialdiff
- Neon-backed alpha database with:
  - 25 breast-cancer-related interventional trials
  - 280 adjacent version patches
  - 122 materiality events
  - 86 generated Evidence Records
- Frozen repository evidence package with:
  - 40 selected Evidence Record JSON files in `records/`
  - `MANIFEST.sha256` for file-level verification
  - `CLAIMS.md` and `NON_CLAIMS.md`
  - `EVIDENCE_RECORD_SCHEMA.md`
  - `VALIDATION.md`
  - `manual-audit-5-records.md`
- Public methodology page covering:
  - 25-study corpus scope
  - critical-triage density denominator
  - deterministic rule taxonomy
  - timing modifier
  - source provenance caveat
  - external literature context
  - commercial-alternative positioning
- Two in-corpus case-study pages:
  - Case Study A: NCT01441947 v16 to v17, secondary-outcome Evidence Record
  - Case Study B: NCT02942355 v26 to v27, late-stage timeline movement

## What Is Excluded

- The alpha corpus is not a representative sample of ClinicalTrials.gov, oncology trials, or breast-cancer trials generally.
- The alpha does not claim misconduct, wrongdoing, sponsor intent, scientific unjustifiability, manuscript non-disclosure, or regulatory non-compliance.
- Evidence Records are generated only for events carrying high and critical triage labels in v0.1-alpha. Medium and low materiality events remain part of the database but are not first-class exported Evidence Records.
- The five-record manual audit is a structural audit of provenance, rule attribution, source fields, and claim boundaries. It is not a severity-calibration audit.
- Case studies must use in-corpus Evidence Records unless a future release explicitly imports additional trials.

## What Is Deferred

- 100-study breast-cancer corpus expansion.
- NCT01275677 as a stronger post-completion outcome-removal case study.
- Broader severity-calibration audit across critical, high, medium, and low tiers. This later failed to validate severity as review priority; see `SEVERITY_CALIBRATION_v0.2.1.md` and `SEVERITY_DECOUPLING_v0.2.1.md`.
- Multi-indication expansion.
- Cross-jurisdiction registry comparison.
- Phase 2 atlas-style aggregate design-space analysis.

## Current Closure Standard

v0.1-alpha is closed when a reviewer can:

1. open the live demo;
2. inspect an Evidence Record page;
3. view the canonical JSON endpoint;
4. see source/provenance/hash fields;
5. see deterministic rule attribution;
6. understand severity as deterministic uncalibrated triage metadata;
7. read explicit claim and non-claim boundaries;
8. verify the frozen record package against `MANIFEST.sha256`.

All eight conditions are satisfied for the current alpha package.
