# TrialDiff Breast Cancer Corpus Backfill Plan

**Date:** 2026-05-20
**Purpose:** Define the first reproducible real-world corpus for TrialDiff before frontend work.

## Goal

Build an amendment-dense breast cancer corpus that is large enough to stress-test the classifier and small enough to manually audit.

Target:

- 100 to 500 studies
- interventional only
- Phase 2, Phase 3, or Phase 2/3
- condition query: `breast cancer`
- at least 3 ClinicalTrials.gov record versions
- last update posted within 5 years of 2026-05-20

The corpus should be used for:

- classifier distribution sanity checks
- false-positive review
- event-feed demo data
- termination-opacity discovery
- frontend development

## Selection Query

Use the official ClinicalTrials.gov v2 search endpoint for candidate discovery:

```text
GET https://clinicaltrials.gov/api/v2/studies
  ?query.cond=breast cancer
  &pageSize=100
```

Do not depend on undocumented filters for study type or phase in the first selector. Fetch candidates from the official endpoint, then filter locally against the returned JSON:

```text
protocolSection.designModule.studyType == "INTERVENTIONAL"
protocolSection.designModule.phases intersects {"PHASE2", "PHASE3"}
protocolSection.statusModule.lastUpdatePostDateStruct.date >= "2021-05-20"
```

Then call the internal history summary endpoint only for locally eligible candidates:

```text
GET https://clinicaltrials.gov/api/int/studies/{NCT_ID}?history=true
```

Keep candidates where:

```text
len(history.changes) >= 3
```

## Relaxation Rules

If the strict query yields fewer than 100 studies, relax in this order:

1. include Phase 1/2 studies
2. reduce minimum record versions from 3 to 2
3. extend last-update window from 5 years to 7 years

Any relaxation must be written to the corpus metadata.

## Selector Output

The selector should write:

- `corpora/breast_cancer_phase2_3_YYYYMMDD.json`
- `corpora/breast_cancer_phase2_3_YYYYMMDD.txt`

The JSON file should include:

- query name
- generated timestamp
- cutoff date
- filters
- relaxation used
- candidate count before local filters
- eligible count before history filter
- final selected NCT IDs
- per-study metadata:
  - NCT ID
  - title
  - lead sponsor
  - phase
  - status
  - last update date
  - version count

The TXT file should contain one NCT ID per line for ingestion.

## Batched Ingest Plan

Run ingestion from the generated NCT list:

```bash
python3 -m trialdiff.cli init-db --db trialdiff.sqlite3
python3 -m trialdiff.cli ingest \
  --db trialdiff.sqlite3 \
  --nct-file corpora/breast_cancer_phase2_3_YYYYMMDD.txt \
  --corpus-label breast-cancer-phase2-3-v1 \
  --delay-seconds 0.25
python3 -m trialdiff.cli classify --db trialdiff.sqlite3
```

Recommended operating discipline:

- start with `--limit 25` in selector
- ingest/classify the first 25
- inspect severity distribution
- scale to 100
- only then scale to 500

## Sanity Checks

After classification:

```sql
select severity, category, count(*)
from materiality_events
group by severity, category
order by severity, category;
```

```sql
select nct_id, from_version, to_version, severity, category, timing_context
from materiality_events
where severity in ('critical', 'high')
order by nct_id, from_version
limit 50;
```

```sql
select nct_id, from_version, to_version, value_signals_json
from materiality_events
where value_signals_json like '%why_stopped%'
   or value_signals_json like '%enrollment_zeroed%';
```

Use the CLI for spot checks:

```bash
python3 -m trialdiff.cli inspect --db trialdiff.sqlite3 NCT05094102
```

## Expected Failure Modes

1. DNS/network failure.

Mitigation:

- retry later; the selector is idempotent and read-only.

2. Internal `/api/int` history failure for some studies.

Mitigation:

- exclude those from historical corpus for now
- still ingest official snapshots if they are in the final list

3. Too many administrative events.

Mitigation:

- tune classifier rules after reviewing distribution
- do not hide raw patches

4. Too few critical/high events.

Mitigation:

- verify whether rule patterns are too narrow
- inspect module labels from high-version studies

## Why A Before Frontend

The frontend should present real signal, not scaffolding. The corpus run will reveal:

- which rule categories dominate
- whether primary/secondary outcome changes are being found
- whether timing modifier escalation is too aggressive
- whether contact/date noise is under control
- whether termination-opacity cases exist in the initial corpus

That information should shape the frontend event feed and filters.
