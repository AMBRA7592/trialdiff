# TrialDiff Wild Scout Memo - 2026-05-19

> **Archived historical memo (2026-05-19).** The original technical unlock: ClinicalTrials.gov's undocumented internal history endpoints expose structured version diffs. Still accurate as capability description; its severity framing ("review priority") was later retracted — see `../../SEVERITY_DECOUPLING_v0.2.1.md`.

## Executive Finding

The most valuable finding is implementation-level, not market-level:

ClinicalTrials.gov's documented public v2 API appears to expose current study records, metadata, statistics, and API version data, but not full record history as a documented endpoint. However, the modern ClinicalTrials.gov frontend itself calls an undocumented public internal endpoint:

- `https://clinicaltrials.gov/api/int/studies/{NCT_ID}?history=true`
- `https://clinicaltrials.gov/api/int/studies/{NCT_ID}/history/{VERSION}`
- `https://clinicaltrials.gov/api/int/studies/{NCT_ID}/history/{VERSION}?patchToVersion={NEXT_VERSION}`

This returns structured study history, including:

- `history.changes`: version number, submitted date, status, study type, changed module labels
- `history.originalData`: original enrollment, sponsor, and original outcome data flags
- `history.lastUpdateVersions`: module-level last-update references
- per-version study snapshots
- JSON Patch style diffs between versions

This is the practical unlock for TrialDiff. The idea is not merely viable; the data needed for a compelling prototype is already structurally accessible.

The caveat: `/api/int` is not documented as a stable public API. It should be used carefully for prototype/backfill and not treated as the only production foundation.

## What This Changes In The Product Spec

The previous spec should not say "ClinicalTrials.gov's API exposes version history" without qualification.

More accurate:

> The documented ClinicalTrials.gov v2 API exposes current study records. Historical record data is available through the public website and appears to be retrievable through the site's internal `/api/int` endpoints, but these endpoints are undocumented. Therefore TrialDiff should use the official v2 API and RSS feeds for durable discovery/current-state tracking, while using internal history endpoints cautiously for prototype backfill and case-study generation.

Recommended data architecture changes:

1. Use official `/api/v2/studies` and ClinicalTrials.gov RSS for watchlist discovery and daily change detection.
2. Store your own snapshots from day one so TrialDiff is not dependent on undocumented history access for future changes.
3. Use `/api/int/studies/{NCT_ID}?history=true` for historical backfill and MVP case studies.
4. Use `/api/int/studies/{NCT_ID}/history/{version}?patchToVersion={next}` to retrieve machine-readable diffs instead of scraping HTML.
5. Keep a clear "data provenance" field in the database: `official_v2`, `rss`, `ctgov_internal_history`, `self_snapshot`.

## Why This Is Strategically Valuable

The competitive gap is sharper than expected.

AACT, the main open relational ClinicalTrials.gov database, explicitly includes current public protocol/results data and updates daily, but says the history of changes to study records is not included. It also warns that static downloads lose the history of changes made to fields.

That means TrialDiff is not just a nicer UI over AACT. It targets a missing temporal layer:

> Who changed what, when, and does the change matter?

This is the core product surface.

## External Tailwinds Found

1. FDA attention has increased.

On April 13, 2026, FDA announced that it had reminded more than 2,200 sponsors and researchers to disclose trial results. FDA said those messages were associated with more than 3,000 registered trials and that an internal analysis found 29.6% of studies highly likely to fall under mandatory reporting requirements had no results information submitted.

This makes the transparency angle timely, not academic.

2. FDAAA TrialsTracker exists, but covers a different layer.

FDAAA TrialsTracker tracks results-reporting compliance for applicable trials. TrialDiff should not compete head-on with it. TrialDiff should own protocol mutation, endpoint/design changes, status transitions, and vague termination reasoning.

3. AACT is a powerful source, but not a version-history product.

AACT can remain useful for current-state relational analysis and broad registry statistics. TrialDiff's distinctive layer is historical change intelligence.

4. CTIS/EU transparency is improving, but it creates a second-phase opportunity, not the MVP.

EU CTIS transparency rules became applicable in June 2024, and by January 31, 2025 ongoing EU/EEA trials had moved under the Clinical Trials Regulation. Cross-registry divergence between ClinicalTrials.gov and CTIS could become a future TrialDiff module, but it is not the first build.

## Concrete Endpoint Tests

Tested study:

- `NCT04362150`
- Internal history summary endpoint returned keys: `history`, `study`, `topics`.
- `history.changes` returned 9 versions.
- `history.changes[0]` contained version `0`, date `2020-04-23`, status `NOT_YET_RECRUITING`.
- `history.changes[-1]` contained version `8`, date `2025-06-09`, status `RECRUITING`, module label `Study Status`.

Tested diff endpoint:

- `https://clinicaltrials.gov/api/int/studies/NCT04362150/history/4?patchToVersion=5`
- Returned JSON Patch operations such as:
  - replace `/protocolSection/statusModule/statusVerifiedDate`
  - replace `/protocolSection/statusModule/lastUpdateSubmitDate`
  - replace `/protocolSection/contactsLocationsModule/centralContacts/0/name`

This means the MVP does not need brittle page scraping for record diffs.

## Case Study Candidate

NCT05094102 - "Intraoperative Evaluation of Axillary Lymphatics"

Sponsor:

- University of Wisconsin, Madison

Why it is useful:

- It has 19 record versions.
- Version 2, submitted 2021-11-05, changed `Outcome Measures`.
- The patch from version 1 to version 2 included:
  - replacement of primary outcome measure text
  - replacement of primary outcome descriptions
  - replacement of primary outcome time frames
  - removal of primary outcome entries
  - replacement/removal of secondary outcome entries

This is exactly the kind of material protocol-change event TrialDiff should surface.

Important caveat:

This example is not presented as misconduct. It is a demonstration that material changes are structurally detectable and currently buried inside record history.

## Revised MVP

### Week 1: History Harvester

Build a small service that accepts a list of NCT IDs and stores:

- current official v2 record
- internal history summary
- per-version metadata
- version-to-version JSON Patch
- changed module labels

Start with 100 to 500 studies in one indication, such as breast cancer, NSCLC, or Alzheimer's disease.

### Week 2: Materiality Classifier

Start deterministic before using an LLM.

Priority rules:

- Critical: primary outcome added, removed, renamed, or time frame changed
- Critical: comparator, randomization, masking, allocation, phase, or arm/intervention structure changed
- High: eligibility criteria materially changed after recruitment started
- High: enrollment target materially reduced/increased
- High: status changes to terminated/suspended/withdrawn
- Medium: completion dates pushed, recruitment status changes, site/country changes
- Low: contact details, administrative updates, spelling/formatting, verification dates

Then use an LLM only to produce a concise analyst-readable explanation of high/critical diffs.

### Week 3: Public Demo

Build a searchable frontend with:

- NCT ID search
- sponsor filter
- indication filter
- timeline of versions
- severity tags
- raw patch view
- plain-language "why this matters" summary

The demo should emphasize:

- "This is a transparency aid, not an accusation engine."
- "All signals are derived from public registry data."
- "Severity means review priority, not proven wrongdoing."

## Database Shape

Recommended tables:

- `trials`
  - `nct_id`
  - `brief_title`
  - `lead_sponsor`
  - `condition_terms`
  - `intervention_terms`
  - `overall_status`
  - `phase`
  - `last_update_posted`
  - `current_record_json`

- `trial_versions`
  - `nct_id`
  - `version`
  - `submitted_date`
  - `overall_status`
  - `study_type`
  - `module_labels`
  - `source`

- `trial_patches`
  - `nct_id`
  - `from_version`
  - `to_version`
  - `patch_json`
  - `changed_paths`
  - `changed_modules`
  - `fetched_at`

- `materiality_events`
  - `nct_id`
  - `from_version`
  - `to_version`
  - `severity`
  - `category`
  - `deterministic_reasons`
  - `llm_summary`
  - `needs_human_review`

## The Main Risk

The hidden `/api/int` endpoint is publicly accessible and used by the ClinicalTrials.gov frontend, but it is undocumented. It can change without notice.

Mitigation:

- use official v2 API and RSS for ongoing durable tracking
- cache history results
- keep request volume low
- clearly label internal-history data provenance
- build a fallback path where TrialDiff creates its own history from future snapshots

## Best Framing

TrialDiff should be framed as:

> A public-interest protocol integrity monitor that turns ClinicalTrials.gov record history into structured, reviewable change intelligence.

Not:

- a short-seller tool
- a pharma accusation machine
- a generic trial search tool
- a replacement for FDAAA TrialsTracker

The immediate value is that it makes an existing but buried transparency layer machine-readable, searchable, and triaged by materiality.

## Sources

- ClinicalTrials.gov API documentation: https://clinicaltrials.gov/data-about-studies/learn-about-api
- ClinicalTrials.gov OpenAPI spec: https://clinicaltrials.gov/api/oas/v2
- ClinicalTrials.gov RSS feeds: https://clinicaltrials.gov/find-studies/rss
- AACT points to consider: https://aact.ctti-clinicaltrials.org/points_to_consider
- AACT update policy: https://aact.ctti-clinicaltrials.org/update_policy
- FDA April 13, 2026 transparency announcement: https://www.fda.gov/news-events/press-announcements/fda-reminds-more-2200-sponsors-and-researchers-disclose-trial-results
- FDA notices of noncompliance and civil money penalties: https://www.fda.gov/science-research/fdas-role-clinicaltrialsgov-information/clinicaltrialsgov-notices-noncompliance-and-civil-money-penalty-actions
- FDAAA TrialsTracker: https://fdaaa.trialstracker.net/
- Bennett Institute TrialsTracker page: https://www.bennett.ox.ac.uk/trialstracker/
- EU CTIS overview: https://www.ema.europa.eu/en/human-regulatory-overview/research-development/clinical-trials-human-medicines/clinical-trials-information-system
- EU Clinical Trials Regulation page: https://health.ec.europa.eu/medicinal-products/clinical-trials/clinical-trials-regulation-eu-no-5362014_en
- BMJ note on ClinicalTrials.gov historical versions: https://www.bmj.com/content/361/bmj.k1452
- CTG-DB adjacent work on cross-trial safety analysis: https://arxiv.org/abs/2603.15936
- TrialPanorama adjacent work on AI for clinical research: https://arxiv.org/abs/2505.16097
