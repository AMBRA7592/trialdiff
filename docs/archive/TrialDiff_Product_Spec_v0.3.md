# TrialDiff Product Spec v0.3

> **Archived historical design document (2026-05-20).** The severity-as-review-priority framing and the timing-escalation design in this spec were retracted/disabled after the v0.2/v0.2.1 calibration — see `../../SEVERITY_DECOUPLING_v0.2.1.md` and `../../V0.2.1_RULE_TIGHTENING_DIAGNOSTIC.md`. Spec numbering does not track releases; see `../../VERSIONS.md`.

**Date:** 2026-05-20
**Status:** Build-facing draft
**Supersedes:** v0.2 build-facing draft
**Core revision:** TrialDiff consumes structured ClinicalTrials.gov history patches where available, classifies materiality deterministically, applies timing as an auditable cross-cutting severity modifier, and runs its own snapshot pipeline from day one for resilience.

## 1. Product Definition

TrialDiff is a public-interest protocol integrity monitor for ClinicalTrials.gov study records.

It turns buried study-record version history into structured, searchable, review-prioritized change intelligence:

> Who changed what, when, and does the change deserve scrutiny?

TrialDiff is not an accusation engine. It does not infer misconduct. It assigns review priority to public registry changes.

Frontend language should state:

> Severity means review priority, not proven wrongdoing.

## 2. What Changed From v0.1

The v0.1 concept assumed TrialDiff would build a full field-level diff engine over study-record snapshots. That is no longer the right architecture.

The scouting finding shows that the modern ClinicalTrials.gov frontend calls public internal endpoints under `/api/int` that return structured history and JSON Patch style deltas:

- `https://clinicaltrials.gov/api/int/studies/{NCT_ID}?history=true`
- `https://clinicaltrials.gov/api/int/studies/{NCT_ID}/history/{VERSION}`
- `https://clinicaltrials.gov/api/int/studies/{NCT_ID}/history/{VERSION}?patchToVersion={NEXT_VERSION}`

This changes the build profile:

- v0.1: build a diff engine, then classify changes.
- v0.2: consume JSON Patches, normalize paths, classify materiality, summarize high-signal events, and store independent snapshots for future resilience.

The intellectual core moves from "diff generation" to "materiality classification."

v0.3 adds three implementation sharpenings:

- timing context is a cross-cutting modifier, not a special case buried inside individual rules
- value signals compose explicitly with path/op rules
- the first breast cancer corpus has a reproducible selection definition

## 3. Non-Negotiable Design Principles

1. Deterministic first.

The materiality classifier should be an auditable rules layer before any LLM is used.

2. LLMs explain, they do not decide.

LLMs may produce concise analyst-readable summaries and assist with semantic equivalence checks. They should not be the primary source of severity assignment in the MVP.

3. Snapshot from day one.

The undocumented `/api/int` endpoints are useful for backfill and case studies, but TrialDiff must collect its own current-record snapshots immediately. If `/api/int` breaks later, TrialDiff should continue diffing future changes from its own stored history.

4. Provenance is a first-class field.

Every stored record, version, patch, and event needs source metadata.

5. Public-interest framing.

The product should help researchers, analysts, journalists, sponsors, and patients inspect registry changes. It should avoid accusatory copy.

## 4. Target Users

Primary MVP users:

- clinical trial transparency researchers
- investigative health journalists
- biotech/pharma analysts
- portfolio reviewers and diligence teams
- technically literate life sciences professionals

Secondary later users:

- academic meta-research groups
- payer/HTA analysts
- reinsurance or risk analytics teams
- pharma clinical operations teams
- patient advocacy organizations

## 5. MVP Scope

The MVP should cover 100 to 500 studies in one indication.

Recommended initial indications:

- breast cancer: easy to understand, high volume, many protocol changes
- non-small cell lung cancer: strong endpoint/comparator relevance
- Alzheimer's disease: good for controversial case-study validation

Recommended first choice:

> Breast cancer for the live demo corpus, plus a small curated validation set for Aduhelm and termination-opacity cases.

Do not start with all Phase 2+ interventional trials from the last 5 years. That is feasible later, but it is less demoable and creates avoidable noise in the first build.

### First Corpus Selection Definition

The initial breast cancer corpus should be reproducible and amendment-dense:

- condition query: `breast cancer`, with MeSH/condition expansion added later if needed
- study type: interventional
- phase: Phase 2, Phase 3, or Phase 2/3
- record history: at least 3 submitted versions
- last update posted: within the last 5 years
- target size: 100 to 500 studies after filtering

If the strict query yields too few studies, relax in this order:

1. include Phase 1/2 oncology studies
2. reduce the version-count threshold from 3 to 2
3. extend last update window from 5 years to 7 years

The corpus query and any relaxation should be stored as run metadata so the demo can be reproduced.

## 6. Data Sources

### Official Durable Sources

Use these for ongoing discovery and current-state tracking:

- ClinicalTrials.gov v2 API: `/api/v2/studies`
- ClinicalTrials.gov v2 single-study endpoint: `/api/v2/studies/{NCT_ID}`
- ClinicalTrials.gov RSS feeds for update discovery

### Prototype Backfill Source

Use cautiously:

- `/api/int/studies/{NCT_ID}?history=true`
- `/api/int/studies/{NCT_ID}/history/{VERSION}`
- `/api/int/studies/{NCT_ID}/history/{VERSION}?patchToVersion={NEXT_VERSION}`

These endpoints are publicly reachable and used by the ClinicalTrials.gov frontend, but they are undocumented and can change without notice.

### Future Optional Sources

- AACT for relational current-state analysis
- CTIS for EU cross-registry comparison
- publications/PMIDs for protocol-to-paper divergence
- FDA notices/noncompliance pages for compliance context

## 7. Data Provenance Model

Use a consistent source enum:

- `official_v2`
- `clinicaltrials_rss`
- `ctgov_internal_history`
- `self_snapshot`
- `manual_case_study`
- `derived_classifier`
- `llm_summary`

Every table that stores externally derived or computed data should include:

- `source`
- `source_url`
- `fetched_at`
- `source_version` where applicable
- `raw_hash`

## 8. System Architecture

### Pipeline Overview

1. Discover study IDs.

Use official v2 API queries and/or RSS feeds to identify the MVP corpus.

2. Fetch current study record.

Use official v2 single-study endpoint and store the normalized current record.

3. Snapshot current record.

Store a full JSON snapshot with hash, timestamp, and provenance.

4. Backfill history if available.

Call internal history summary and per-version patch endpoints.

5. Normalize patches.

Extract JSON Patch operations, paths, modules, and field families.

6. Classify materiality.

Apply deterministic path/value rules.

7. Generate summaries.

Use LLM only for high/critical events, and only after deterministic classification.

8. Serve UI/API.

Expose study timelines, patch details, severity tags, and summaries.

### Resilience Strategy

Run two tracks from day one:

- Track A: historical backfill from `/api/int`
- Track B: self-collected daily snapshots from official v2 API

If Track A breaks, Track B still supports future diffs.

### Patch Semantics

The internal endpoint's version patch should be treated as a structured delta from one study-record version to another. For adjacent comparisons, TrialDiff should call:

- `/api/int/studies/{NCT_ID}/history/{FROM_VERSION}?patchToVersion={TO_VERSION}`

Use adjacent versions for MVP materiality classification:

- from version `0` to `1`
- from version `1` to `2`
- from version `n` to `n+1`

JSON Patch operations provide `op` and `path`, and usually the new `value` for `add` and `replace`. They do not always provide the old value. For before/after rendering:

1. Fetch or store the `FROM_VERSION` study JSON.
2. Resolve the JSON Pointer path against `FROM_VERSION` to get the old value.
3. Apply the patch to reconstruct `TO_VERSION`.
4. Resolve the same path against reconstructed `TO_VERSION` to get the new value.

For `remove`, the old value is the value at the removed path in `FROM_VERSION`; the new value is null/absent. For array paths, preserve enough sibling context to avoid misleading summaries when indexes shift.

### Self-Snapshot Diffs

The self-snapshot pipeline should not recreate a bespoke semantic diff engine. If `/api/int` is unavailable, generate generic RFC 6902-style patches between official v2 snapshots using an existing JSON Patch library, then feed those patches into the same normalization/classification layer.

This means `trial_patches` can hold both:

- `ctgov_history_patch`: backfilled historical patches from `/api/int`
- `self_snapshot_patch`: future patches generated from TrialDiff's own stored snapshots

The materiality classifier should not care which source produced the patch, as long as provenance is preserved.

## 9. Database Schema

The schema can start in SQLite for local development and move to Postgres/Supabase/Neon for deployment.

### `trials`

- `nct_id` primary key
- `brief_title`
- `official_title`
- `lead_sponsor`
- `lead_sponsor_class`
- `conditions_json`
- `interventions_json`
- `overall_status`
- `phase_json`
- `study_type`
- `last_update_posted`
- `first_submitted_date`
- `has_results`
- `current_record_json`
- `current_record_hash`
- `source`
- `source_url`
- `fetched_at`

### `trial_snapshots`

- `id` primary key
- `nct_id`
- `snapshot_date`
- `record_json`
- `record_hash`
- `source`
- `source_url`
- `fetched_at`

Unique constraint:

- `nct_id`, `record_hash`

### `trial_versions`

- `id` primary key
- `nct_id`
- `version`
- `submitted_date`
- `overall_status`
- `study_type`
- `module_labels_json`
- `review_not_passed`
- `unposted_events_json`
- `source`
- `source_url`
- `fetched_at`

Unique constraint:

- `nct_id`, `version`

### `trial_patches`

- `id` primary key
- `nct_id`
- `from_version`
- `to_version`
- `patch_kind`
- `patch_json`
- `patch_hash`
- `changed_paths_json`
- `changed_modules_json`
- `op_counts_json`
- `source`
- `source_url`
- `fetched_at`

Unique constraint:

- `nct_id`, `from_version`, `to_version`, `patch_hash`

### `materiality_events`

- `id` primary key
- `nct_id`
- `from_version`
- `to_version`
- `submitted_date`
- `timing_context`
- `severity_pre_timing`
- `severity`
- `category`
- `changed_paths_json`
- `deterministic_rules_json`
- `value_signals_json`
- `summary`
- `summary_source`
- `needs_human_review`
- `created_at`

### `classifier_rules`

- `id` primary key
- `rule_key`
- `path_pattern`
- `op_filter_json`
- `value_filter_json`
- `severity`
- `category`
- `timing_sensitive`
- `description`
- `active`
- `created_at`

### `case_studies`

- `id` primary key
- `nct_id`
- `case_type`
- `status`
- `public_claim_level`
- `notes`
- `verified_at`

## 10. Materiality Classifier

The classifier should evaluate every JSON Patch operation as:

- path signal
- operation signal
- value signal
- timing signal
- status context

The classifier stores both base and final severity:

- `severity_pre_timing`: severity from path/op/value rules alone
- `timing_context`: lifecycle context at the `FROM_VERSION`
- `severity`: final severity after timing modifier

### Severity Levels

- `critical`: material protocol/design/outcome/status change deserving immediate review
- `high`: potentially material change requiring inspection
- `medium`: relevant operational/timeline signal
- `low`: mostly administrative
- `ignore`: known noise

### Category Labels

- `primary_outcome_change`
- `secondary_outcome_change`
- `design_change`
- `arm_intervention_change`
- `eligibility_change`
- `enrollment_change`
- `status_termination`
- `timeline_shift`
- `location_or_site_change`
- `administrative_contact_change`
- `results_submission_change`
- `document_change`
- `unknown_material_change`

### Timing Context

Timing is a cross-cutting severity modifier. It should be computed once per patch from the `FROM_VERSION` record, then applied consistently across categories.

Timing contexts:

- `pre_recruitment`: `overallStatus` is `NOT_YET_RECRUITING` or `WITHDRAWN`
- `early_recruitment`: `overallStatus` is `RECRUITING`, `ENROLLING_BY_INVITATION`, or equivalent, and target enrollment progress is below 50 percent or unknown
- `late_recruitment`: `overallStatus` is recruiting/enrolling and target enrollment progress is at least 50 percent
- `post_recruitment`: `overallStatus` is `ACTIVE_NOT_RECRUITING`, `COMPLETED`, `TERMINATED`, or `SUSPENDED`
- `unknown`: status or enrollment context cannot be resolved

MVP implementation note:

ClinicalTrials.gov usually exposes target enrollment, not live accrual. For v0.3, compute late recruitment conservatively. Use `post_recruitment` when status proves recruitment is closed. Use `late_recruitment` only when a reliable progress proxy exists. Otherwise use `early_recruitment` or `unknown`; do not invent precision.

Timing modifier:

- `pre_recruitment`: no escalation
- `early_recruitment`: no escalation by default
- `late_recruitment`: escalate by one level for outcome, design, eligibility, arm/intervention, comparator, and enrollment changes
- `post_recruitment`: escalate by one level for outcome, design, eligibility, arm/intervention, comparator, and enrollment changes
- `unknown`: no escalation, but keep `needs_human_review=true` for high/critical categories

Severity escalation is capped at `critical`.

## 11. Deterministic Rules v0.3

### Composition Rule

Classification is deterministic and compositional:

```text
severity_pre_timing = max(path_rule_severity, op_signal_severity, value_signal_severity)
severity = apply_timing_modifier(severity_pre_timing, timing_context, category)
```

Examples:

- a secondary outcome path normally produces `high`
- if the secondary outcome change occurs in `late_recruitment` or `post_recruitment`, final severity escalates to `critical`
- a `whyStopped` path normally produces `high`
- a low-information or null `whyStopped` value signal may keep it `high` or escalate it according to the value-signal rule
- administrative contact changes remain `low` even if late, because the category is not timing-sensitive

### Critical

Path patterns:

- `/protocolSection/outcomesModule/primaryOutcomes/*`
- `/protocolSection/designModule/designInfo/allocation`
- `/protocolSection/designModule/designInfo/interventionModel`
- `/protocolSection/designModule/designInfo/maskingInfo/*`
- `/protocolSection/designModule/designInfo/primaryPurpose`
- `/protocolSection/designModule/phases/*`
- `/protocolSection/armsInterventionsModule/armGroups/*`
- `/protocolSection/armsInterventionsModule/interventions/*`
- `/protocolSection/statusModule/overallStatus` when new value is `TERMINATED`, `SUSPENDED`, or `WITHDRAWN`

Operation signals:

- `remove` on primary outcome
- `replace` on primary outcome measure, description, or time frame
- `add` or `remove` on arms/interventions
- `replace` on randomization, masking, allocation, intervention model, phase, or primary purpose

### High

Path patterns:

- `/protocolSection/outcomesModule/secondaryOutcomes/*`
- `/protocolSection/eligibilityModule/eligibilityCriteria`
- `/protocolSection/designModule/enrollmentInfo/count`
- `/protocolSection/designModule/enrollmentInfo/type`
- `/protocolSection/statusModule/whyStopped`

Value signals:

- enrollment count changes by more than 20 percent: `high`
- enrollment type changes from anticipated to actual: `high`
- eligibility criteria change after recruitment has started: `high` before timing modifier
- `whyStopped` is empty/null after termination/suspension/withdrawal: `critical`
- `whyStopped` uses low-information phrases: `high`

Low-information phrases for `whyStopped`:

- `business decision`
- `strategic decision`
- `sponsor decision`
- `administrative reasons`
- `feasibility`
- `terminated by sponsor`
- empty/null

Implementation note:

The path `/protocolSection/statusModule/whyStopped` is a high-priority field because it explains trial discontinuation. The value determines whether the event stays `high` or becomes `critical`. A null/empty `whyStopped` after a terminal status change is `critical`; a vague but non-empty phrase is `high` unless timing or another signal escalates it.

### Medium

Path patterns:

- `/protocolSection/statusModule/startDateStruct/*`
- `/protocolSection/statusModule/primaryCompletionDateStruct/*`
- `/protocolSection/statusModule/completionDateStruct/*`
- `/protocolSection/statusModule/overallStatus` for recruiting/completed transitions
- `/protocolSection/contactsLocationsModule/locations/*`

Signals:

- completion date pushed by more than 90 days
- recruitment state changes
- site/country footprint changes

### Low Or Administrative

Path patterns:

- `/protocolSection/contactsLocationsModule/centralContacts/*`
- `/protocolSection/contactsLocationsModule/overallOfficials/*`
- `/protocolSection/statusModule/statusVerifiedDate`
- `/protocolSection/statusModule/lastUpdateSubmitDate`
- `/protocolSection/statusModule/lastUpdatePostDateStruct/*`
- spelling/format-only fields where no semantic path is affected

## 12. LLM Role

The LLM should be called only after deterministic rules have selected an event as `critical` or `high`.

Allowed LLM tasks:

- summarize a material change in plain English
- compare old/new endpoint text for semantic equivalence
- explain why a deterministic rule fired
- produce a reviewer checklist

Disallowed MVP LLM tasks:

- deciding primary severity from scratch
- inferring sponsor intent
- generating claims of misconduct
- replacing deterministic rules

Example output:

> Version 2 changed the primary outcome definitions and removed additional primary outcome entries before recruitment began. This is review-priority critical because primary outcome changes affect how trial success is evaluated. This flag does not imply misconduct.

## 13. API Design

### Internal Build APIs

`POST /api/ingest/studies`

Input:

- list of NCT IDs
- optional corpus label

Action:

- fetch official current record
- store snapshot
- optionally fetch internal history

`POST /api/classify/{nct_id}`

Action:

- classify patches for one study
- persist materiality events

`GET /api/trials`

Filters:

- sponsor
- condition
- severity
- category
- status
- phase

`GET /api/trials/{nct_id}`

Returns:

- current study summary
- versions
- materiality events
- patches

`GET /api/events`

Returns:

- feed of critical/high events

## 14. Frontend MVP

The first screen should be the tool, not a landing page.

Required views:

1. Event feed

- latest critical/high changes
- filters by condition, sponsor, category, severity
- visible disclaimer: "Severity means review priority, not proven wrongdoing."

2. Trial timeline

- versions by submitted date
- status at each version
- changed modules
- severity badges

3. Patch inspector

- raw JSON Patch
- path-grouped summary
- before/after values when available
- deterministic rules that fired

4. Case studies

- curated examples with method notes
- no accusation language
- include raw source links

Optional:

- RSS/email alerts
- sponsor page
- indication landscape page

## 15. Case Study Plan

### Case A: Structural Demo

NCT05094102 - "Intraoperative Evaluation of Axillary Lymphatics"

Purpose:

- show that material outcome-measure changes are structurally detectable
- low political baggage
- good for methodology demo

Current evidence from scout:

- version 2 submitted 2021-11-05 changed `Outcome Measures`
- patch from version 1 to 2 replaced primary outcome measure text, descriptions, and time frames
- patch removed primary and secondary outcome entries

Public claim level:

- safe: "material outcome-measure changes detected"
- avoid: any misconduct implication

### Case B: Controversial Validation Candidate

Aducanumab/Aduhelm EMERGE and ENGAGE trial records.

Likely candidates to verify:

- `NCT02484547`
- `NCT02477800`

Purpose:

- test whether TrialDiff surfaces changes relevant to a known public controversy
- not for first public accusation

Requirement before publication:

- verify NCT IDs
- inspect exact record-history changes
- separate registry changes from sponsor/statistical-analysis controversies

Public claim level:

- cautious: "known controversial program used to test whether registry-history signals are visible"

### Case C: Termination Opacity

Find one terminated/suspended/withdrawn trial where:

- `overallStatus` changes to `TERMINATED`, `SUSPENDED`, or `WITHDRAWN`
- `whyStopped` is empty or low-information
- registry provides no substantive reason

Purpose:

- demonstrate that absence of meaningful explanation is itself a review-priority signal

Public claim level:

- safe: "termination reason field provides limited information"
- avoid: inferring undisclosed safety/efficacy causes

## 16. Build Plan

### Week 1: Harvester And Snapshot Core

Deliverables:

- repo scaffold
- official v2 fetcher
- internal history fetcher
- snapshot storage
- patch storage
- self-snapshot patch generator using an existing JSON Patch library
- provenance fields
- reproducible breast cancer corpus query and run metadata
- CLI command: ingest NCT IDs

Acceptance criteria:

- ingest 100 studies
- select studies using the defined breast cancer corpus filters or record any relaxation used
- store current official v2 snapshots
- store history metadata for studies where `/api/int` succeeds
- store version-to-version patches
- generate at least one self-snapshot patch from two locally stored fixture snapshots
- rerun is idempotent
- if `/api/int` fails, official snapshot still succeeds

### Week 2: Deterministic Classifier

Deliverables:

- path matcher
- rule table
- severity assignment
- materiality event storage
- deterministic explanation strings
- unit tests for rule coverage

Acceptance criteria:

- classify NCT05094102 version 1 to 2 as critical primary outcome change
- classify contact/date verification changes as low/administrative
- classify terminated/suspended/withdrawn status changes as critical
- classify enrollment changes over threshold as high

### Week 3: Demo UI

Deliverables:

- event feed
- trial detail page
- version timeline
- patch inspector
- case study page

Acceptance criteria:

- user can search NCT ID
- user can filter critical/high events
- user can see exactly which rule fired
- raw patch remains accessible
- disclaimer appears near severity badges

### Week 4: Validation And Write-Up

Deliverables:

- 3 curated case studies
- methodology note
- README
- short public essay
- cost section
- limitations section

Acceptance criteria:

- every public claim links to source data
- no language implies misconduct
- methodology is reproducible
- limitations are explicit

## 17. Cost Profile

Expected MVP cost:

- ClinicalTrials.gov API: free
- GitHub Actions cron: free tier
- SQLite local: free
- Supabase/Neon Postgres: free to low-cost
- Vercel frontend/API: free tier
- LLM summaries: negligible if limited to high/critical events

Expected monthly cost:

- local/prototype: $0
- hosted MVP: $0 to $10
- steady small public demo: under $25

Cost is an architectural signal here. A high cloud bill would indicate overbuilding, not sophistication.

## 18. Risks And Mitigations

### Risk: `/api/int` changes or disappears

Mitigation:

- snapshot from day one
- cache backfilled history
- keep low request volume
- separate official-source ingestion from internal-history ingestion
- label `/api/int` as undocumented in docs

### Risk: False implication of wrongdoing

Mitigation:

- "review priority" language
- no intent claims
- raw source links
- deterministic rules visible
- conservative summaries

### Risk: Rule false positives

Mitigation:

- show exact path/op/value
- allow `needs_human_review`
- keep severity explainable
- use case studies for calibration

### Risk: LLM hallucination

Mitigation:

- LLM summaries only after deterministic classification
- pass only old/new values and rule reasons
- require source-linked summaries
- store summary source and model metadata

### Risk: Corpus too broad

Mitigation:

- begin with 100 to 500 studies in one indication
- curate validation cases separately
- expand only after classifier is stable

## 19. Public Positioning

Recommended description:

> TrialDiff is a public-interest protocol integrity monitor that turns ClinicalTrials.gov record history into structured, reviewable change intelligence.

Avoid:

- "catching fraud"
- "exposing pharma"
- "short-seller intelligence"
- "AI judges trial integrity"

Better:

- "registry-history transparency"
- "protocol-change review priority"
- "structured audit trail"
- "public data, explainable rules"

## 20. README Structure

1. What TrialDiff does
2. What TrialDiff does not claim
3. Data sources
4. Why version history matters
5. Architecture
6. Materiality rules
7. Case studies
8. Limitations
9. Cost profile
10. Reproducibility

## 21. Open Questions

1. Which indication should be the first live corpus?

Recommendation: breast cancer.

2. Should the MVP include email/RSS alerts?

Recommendation: no for first public demo; event feed is enough.

3. Should AACT be added immediately?

Recommendation: no. Use it later for broader relational analysis.

4. Should CTIS/EU be included?

Recommendation: no. Treat as Phase 2.

5. Should LLM summaries be enabled from the start?

Recommendation: only behind a flag after deterministic classification works.

## 22. Phase 2 Direction

After the MVP:

- cross-trial landscape view
- endpoint clustering by indication
- comparator migration over time
- coordinated termination/status-change detection
- sponsor-level descriptive dashboards
- CTIS versus ClinicalTrials.gov divergence checks

This is where the sheaf/negative-space intuition becomes product-relevant, but it depends on the v0.2 temporal layer first.

## 23. Definition Of Done For v0.2 MVP

TrialDiff v0.2 is done when:

- it ingests a small indication corpus
- it stores current records and self-snapshots from official v2 API
- it backfills history patches where available
- it classifies materiality deterministically
- it exposes raw patches and fired rules
- it displays a usable timeline and event feed
- it includes at least three curated case studies or validation candidates
- it states limitations clearly
- it can continue collecting future snapshots even if `/api/int` breaks

## 24. Source Notes

Core references from scouting:

- ClinicalTrials.gov API documentation: https://clinicaltrials.gov/data-about-studies/learn-about-api
- ClinicalTrials.gov OpenAPI spec: https://clinicaltrials.gov/api/oas/v2
- ClinicalTrials.gov RSS feeds: https://clinicaltrials.gov/find-studies/rss
- AACT points to consider: https://aact.ctti-clinicaltrials.org/points_to_consider
- AACT update policy: https://aact.ctti-clinicaltrials.org/update_policy
- FDA April 13, 2026 transparency announcement: https://www.fda.gov/news-events/press-announcements/fda-reminds-more-2200-sponsors-and-researchers-disclose-trial-results
- FDAAA TrialsTracker: https://fdaaa.trialstracker.net/
- Bennett Institute TrialsTracker page: https://www.bennett.ox.ac.uk/trialstracker/
