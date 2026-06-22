# TrialDiff Evidence Demo v0.1-alpha

TrialDiff v0.1-alpha is a bounded evidence demo showing that public ClinicalTrials.gov record changes can be converted into replayable, source-linked, deterministic Evidence Records with deterministic triage classifications.

This is not a product launch, monitoring service, pharma SaaS, misconduct detector, or allegation engine.

> Severity is deterministic, reproducible, uncalibrated triage metadata. It is not validated review priority and not proven wrongdoing.

## Live Demo

Live site: <https://trialdiff.vercel.app>

The live demo is backed by Neon Postgres and currently renders the same 25-study alpha corpus used for this frozen package:

- 25 breast-cancer-related interventional trials
- 280 adjacent version patches
- 122 materiality events
- 86 generated Evidence Records
- 40 selected frozen records in `records/`

The alpha is intentionally relabeled as a 25-study demo because the local 100-study SQLite file was not reliably readable at freeze time.

## Frozen Package

This repository snapshot contains:

- `records/*.json` - 40 selected self-contained Evidence Records
- `CLAIMS.md` - what the demo is allowed to claim
- `NON_CLAIMS.md` - what the demo explicitly does not claim
- `EVIDENCE_RECORD_PRIMITIVE.md` - operational primitive specification
- `EVIDENCE_RECORD_SCHEMA.md` - schema description for exported records
- `VALIDATION.md` - validation and audit status
- `RELEASE_NOTES_v0.1-alpha.md` - what exists, what is excluded, and what is deferred
- `manual-audit-5-records.md` - five-record manual audit notes
- `MANIFEST.sha256` - SHA-256 manifest for frozen files
- `scripts/export_alpha_demo.py` - deterministic export script
- `scripts/validate_alpha_demo.py` - package validation script

## Selection Rule

The frozen package exports 40 Evidence Records from the 25-study corpus:

1. all records carrying the critical triage label first;
2. then records carrying the high triage label;
3. ordered by timing context, with post-recruitment and late-recruitment records before earlier records;
4. capped at 40 records.

This produces a deterministic, bounded inspection slice rather than a full product dataset or validated priority feed.

## What A Reviewer Can Inspect

For each exported record, a reviewer can answer:

1. What changed?
2. Where did it change?
3. When did it change?
4. Which deterministic rule or value signal classified it?
5. Which deterministic triage signal caused it to be selected?
6. What source/provenance/hash fields support the record?
7. Can the record be verified against the frozen manifest?
8. What is explicitly not being claimed?

## Regenerate The Frozen Records

From the repository root:

```bash
python3 -m trialdiff.cli generate-evidence \
  --db trialdiff_breast_cancer_limit25.sqlite3 \
  --force

python3 scripts/export_alpha_demo.py \
  --db trialdiff_breast_cancer_limit25.sqlite3 \
  --out records \
  --limit 40
```

## Validate The Frozen Package

```bash
python3 scripts/validate_alpha_demo.py
shasum -a 256 -c MANIFEST.sha256
```

Expected validator output:

```text
records=40
```

## Current Status

Technical proof cleared; 30-day artifact closed as a v0.1 alpha.

The v0.2/v0.2.1 severity calibration failed the review-priority gate. Critical confirmations across fresh rubric applications ranged from 4/30 to 17/30, below the 24/30 required threshold. Severity labels are therefore retained only as deterministic uncalibrated triage metadata. The evidence-record primitive remains supported; the certified-severity claim and buyer-facing priority brief remain blocked. See `EVIDENCE_RECORD_PRIMITIVE.md`, `SEVERITY_CALIBRATION_v0.2.1.md`, and `SEVERITY_DECOUPLING_v0.2.1.md`.
