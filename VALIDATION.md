# Validation

Validation date: 2026-06-17

## Package Checks

The alpha package validates locally with:

```bash
python3 scripts/validate_alpha_demo.py
shasum -a 256 -c MANIFEST.sha256
```

The validator checks:

- 20-40 exported Evidence Records are present;
- every record filename matches its `event_id`;
- every record uses `schema = trialdiff.alpha_demo_record`;
- every exported record is high or critical severity;
- study metadata fields are present;
- classification fields are present;
- provenance fields are present;
- changed paths are non-empty;
- patch operations are non-empty;
- supported claims are non-empty;
- the required misconduct/wrongdoing non-claim is present;
- files match `MANIFEST.sha256`.

## Corpus Counts

The healthy alpha SQLite corpus contains:

- 25 trials
- 280 adjacent patches
- 122 materiality events
- 86 Evidence Records

The frozen package exports 40 selected records:

- 35 critical
- 5 high

## Live Deployment Check

The deployed alpha demo at <https://trialdiff.vercel.app> returned HTTP 200 on 2026-06-17 and rendered corpus counts from the database.

The live Evidence Record pages and canonical JSON endpoints were previously verified after deployment. The frozen package does not require the live site to remain available; each `records/*.json` file is self-contained and hash-verified by the manifest.

## Source-Link Spot Check

For the five records in `manual-audit-5-records.md`, both source link classes returned HTTP 200 on 2026-06-17:

- ClinicalTrials.gov public study page: `text/html`
- ClinicalTrials.gov internal history patch URL: `application/json`

This is a spot check, not a guarantee that ClinicalTrials.gov will preserve every internal history endpoint indefinitely. The frozen record retains patch hashes and exported patch payloads for replay even if a source endpoint later changes.

## Manual Audit

Five records were manually spot-checked in `manual-audit-5-records.md`.

The audit checked:

- event ID and filename consistency;
- NCT ID, title, and sponsor presence;
- version references;
- category/severity/timing fields;
- deterministic rules or value signals;
- changed paths;
- patch hash and canonical hash;
- explicit non-claims.

The audit did not adjudicate scientific justification, misconduct, sponsor intent, publication disclosure, or regulatory compliance.
