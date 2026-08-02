# TrialDiff — Product Specification (v1.1)

> **Archived historical design document (2026-05-21).** Despite the highest version number, this spec predates the shipped v0.1-alpha release, and it is the most retracted document in the repository: the buyer-facing severity brief it plans was permanently blocked when the v0.2/v0.2.1 calibration failed its gate (`../../SEVERITY_DECOUPLING_v0.2.1.md`). The referenced "v1.0" spec never existed as a document. See `../../VERSIONS.md`.

**Status:** Build-state spec revision after external market scan. Supersedes v1.0 positioning while preserving v1.0 ship discipline.

**Date:** 2026-05-21

**Core revision:** TrialDiff is not positioned as the only system that detects ClinicalTrials.gov changes. Commercial change-alert products now exist. TrialDiff's defensible lane is an **open, reproducible amendment evidence layer**: stable event records with provenance, hashes, deterministic rules, timing context, claims-supported / claims-not-supported framing, and citeable URLs.

---

## 1. Executive Summary

TrialDiff is public-interest research infrastructure for ClinicalTrials.gov amendment history.

It continuously ingests trial versions, stores JSON Patch diffs, classifies material amendments through deterministic rules, and exposes high-priority events as inspectable, reproducible, citeable evidence records.

TrialDiff does **not** allege misconduct, score sponsor reputation, or infer intent. Every severity label means **review priority**, not wrongdoing.

The v1.1 positioning is:

> Commercial tools already monitor clinical trial changes. TrialDiff's purpose is different: to create an open, reproducible amendment evidence layer for public-interest research, journalism, and methodological review.

## 2. Strategic Positioning Change

### Previous claim, now too broad

> No tool systematically monitors, classifies, or surfaces material protocol amendments at corpus scale.

This is no longer safe as a core claim. RxDataLab markets daily ClinicalTrials.gov trial-change detection across 450K+ records, including status, endpoint, enrollment, result, and change tracking. DataLookout markets daily ClinicalTrials.gov monitoring with endpoint modifications, enrollment shifts, severity labels, email alerts, and CSV export.

Sources:

- [RxDataLab pricing / platform page](https://rxdatalab.com/pricing/)
- [DataLookout Clinical Trial Monitoring](https://datalookout.com/clinical-trial-monitoring)

### Revised claim

> Commercial alert products monitor registry changes, but TrialDiff exposes an open, reproducible, severity-attributed amendment evidence corpus with per-event provenance, deterministic rules, source hashes, and review-ready case records.

### Practical implication

TrialDiff should not compete as a private watchlist, alert feed, or commercial pipeline-intelligence dashboard. It should compete on:

- reproducibility
- provenance
- public inspectability
- stable citation
- deterministic rule transparency
- neutral claims discipline
- research-grade methodology

## 3. Product Definition

TrialDiff has three public surfaces:

1. **Dashboard** — aggregate and trial-level navigation over material amendment events.
2. **Patch Inspector** — human-readable inspection of one adjacent-version JSON Patch with before/after values and rule attribution.
3. **Amendment Evidence Record** — stable, citeable event page plus canonical JSON for high/critical events.

The dashboard is for discovery. The patch inspector is for browsing. The evidence record is for citation and public review.

## 4. Architecture

```
GitHub Actions cron
  -> Python trialdiff CLI
     -> official v2 snapshots
     -> /api/int history + adjacent JSON Patches
     -> deterministic classifier
  -> Neon Postgres
     -> trials
     -> trial_versions
     -> trial_patches
     -> materiality_events
     -> classifier_rules
  -> Astro SSR frontend on Vercel
     -> raw SQL via postgres.js
     -> no ORM
     -> server-rendered patch inspector using <details>
```

Architecture decisions are now fixed for v1.x:

- **Pipeline:** Python
- **Database:** Neon Postgres
- **Frontend:** Astro SSR
- **Data access:** raw SQL through `postgres.js` tagged templates
- **Interactivity:** default to server-rendered HTML; add islands only when native HTML is insufficient
- **Cron:** GitHub Actions

React is not part of v1.1 unless a genuinely interactive component justifies it later. The patch inspector is server-rendered.

## 5. Evidence Record Model

### Name

Use **Amendment Evidence Record**, not "packet," in public UI and methodology text.

Short label in navigation: **Evidence Record**.

### Stable event identifier

Public event IDs should be deterministic and reproducible:

```text
evt_{NCT_ID}_v{FROM_VERSION}_v{TO_VERSION}_{EVENT_HASH8}
```

`EVENT_HASH8` is the first 8 characters of a SHA-256 hash over the canonical tuple:

```json
{
  "nct_id": "...",
  "from_version": 1,
  "to_version": 2,
  "patch_hash": "...",
  "category": "...",
  "changed_paths": [...],
  "rule_set_hash": "..."
}
```

Including `rule_set_hash` makes the evidence record reproducible under a specific taxonomy version. If rules change later, reclassified records can get new event IDs while preserving prior records.

### Human page

Route:

```text
/events/{event_id}
```

The page shows:

- NCT ID
- trial title and sponsor
- from/to versions
- submitted date
- severity before timing
- final severity
- timing context
- category and all categories
- exact changed paths
- exact JSON Patch operations relevant to the event
- before/after values where reconstructable
- deterministic rules fired
- value signals
- source and source URL
- patch hash
- from/to snapshot hashes
- rule set hash
- review question
- claims supported
- claims not supported
- citation block
- canonical JSON link

### Canonical JSON

Route:

```text
/events/{event_id}.json
```

Minimum shape:

```json
{
  "event_id": "evt_NCT01275677_v23_v24_a3f2b1c0",
  "nct_id": "NCT01275677",
  "from_version": 23,
  "to_version": 24,
  "submitted_date": "2024-01-01",
  "severity_pre_timing": "high",
  "severity": "critical",
  "category": "secondary_outcome_change",
  "categories": ["secondary_outcome_change", "results_submission_change"],
  "timing_context": "post_recruitment",
  "changed_paths": [],
  "deterministic_rules": [],
  "value_signals": [],
  "from_snapshot_hash": "...",
  "to_snapshot_hash": "...",
  "patch_hash": "...",
  "rule_set_hash": "...",
  "source": "ctgov_internal_history",
  "source_url": "https://clinicaltrials.gov/...",
  "claims_supported": [],
  "claims_not_supported": [],
  "review_question": "...",
  "generated_at": "2026-05-21T00:00:00Z"
}
```

### Claims discipline

Every Evidence Record should explicitly separate supported and unsupported claims.

Example:

```json
"claims_supported": [
  "A secondary outcome was removed between version 23 and version 24.",
  "The change occurred after the trial had reached a terminal recruitment status.",
  "The event was classified by deterministic rule secondary_outcome_any_change."
],
"claims_not_supported": [
  "That the modification was scientifically unjustified.",
  "That this constitutes a regulatory violation.",
  "That sponsor intent can be inferred from this change.",
  "That the trial outcome was affected by this modification."
]
```

This structure is required. It is the main safeguard that distinguishes evidence infrastructure from accusation infrastructure.

### Review question

Each Evidence Record should include one neutral review question.

Examples:

- "Does the protocol amendment history explain why this outcome changed after completion?"
- "Is the terminal-status explanation complete enough for public-record review?"
- "Does the before/after endpoint wording represent a substantive endpoint change or a clarification?"

## 6. Data Model Additions

No separate physical table is required for v1.1 if Evidence Records can be generated as a view over existing tables.

Minimum implementation options:

1. **Computed view:** derive `event_id`, claims, citation metadata, and evidence JSON from `materiality_events`, `trial_patches`, `trial_versions`, `trials`, and `classifier_rules`.
2. **Materialized table later:** add `amendment_evidence_records` only if generation becomes expensive or if records need immutable publication snapshots.

### Required fields in evidence view

- `event_id`
- `nct_id`
- `brief_title`
- `lead_sponsor`
- `from_version`
- `to_version`
- `submitted_date`
- `severity_pre_timing`
- `severity`
- `category`
- `categories_json`
- `timing_context`
- `changed_paths_json`
- `deterministic_rules_json`
- `value_signals_json`
- `from_snapshot_hash`
- `to_snapshot_hash`
- `patch_hash`
- `rule_set_hash`
- `source`
- `source_url`
- `claims_supported_json`
- `claims_not_supported_json`
- `review_question`
- `canonical_json`

## 7. Frontend Lenses

v1.1 homepage has four lenses:

1. **Post-completion material edits**
   - Highest public-interest lens.
   - Shows material outcome/result/design/status changes after completion or terminal status.
   - Directly supported by published oncology evidence.

2. **Recent material activity**
   - Reverse-chronological feed of critical/high events.
   - The "what changed recently" operational lens.

3. **Critical density**
   - Trials ranked by critical events / total patches.
   - Minimum `patch_count >= 10`.
   - Tooltip / methodology link must state denominator clearly.

4. **Amendment intensity**
   - Trials ranked by total patch count.
   - Useful for platform protocols and long-running studies.
   - Explicitly not a proxy for consequentiality.

The default public landing can remain Recent for operational freshness, but the post-completion lens should be visually promoted as the flagship research surface.

## 8. Published Evidence Context

The post-completion lens is grounded in the JAMA Network Open oncology endpoint-change paper:

- 145/755 cancer phase 3 randomized trials had primary endpoint changes (19.2%).
- ClinicalTrials.gov detected 120/755 (15.9%).
- 102/145 trials with endpoint changes did not disclose those changes in the manuscript (70.3%).
- The paper concludes that endpoint changes were frequent and underreported, and mostly occurred after reported study completion dates.

Source: [JAMA Network Open, Florez et al. 2023](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2805005)

TrialDiff should not claim to reproduce this study in v1.1. It should use the paper as external motivation and a comparator for future validation.

## 9. `whyStopped` Framing

`whyStopped` is no longer framed as a generic transparency preference.

42 CFR § 11.64 states that if Overall Recruitment Status changes to suspended, terminated, or withdrawn, the responsible party must submit the Why Study Stopped data element.

Source: [42 CFR § 11.64](https://www.law.cornell.edu/cfr/text/42/11.64)

v1.1 wording:

> Empty or low-information termination explanations are classified as review-priority public-record quality signals. TrialDiff does not infer sponsor motive or regulatory violation.

This language should appear in:

- methodology page
- Evidence Record pages for `whyStopped` events
- README positioning

## 10. Results-Clock Context

For completed or terminated trials, Evidence Records may include light results-clock context:

- primary completion date
- completion date
- has results posted
- whether material change occurred after completion
- whether results-context data are available

Do **not** implement legal compliance scoring in v1.1.

Allowed wording:

> Results-clock context is provided to orient review. TrialDiff does not determine FDAAA compliance.

## 11. Patch Inspector

The patch inspector remains a browsing surface, not the stable citation object.

v1.1 inspector requirements:

- server-rendered Astro component
- path-grouped operation list
- administrative groups collapsed by default
- before/after values for `replace`
- inserted/removed values for `add`/`remove`
- per-operation severity inferred by re-applying path rules
- matched rules shown per operation
- provenance shown in header
- LLM summary slot present but empty or "Manual review pending"
- raw JSON Patch expandable

The Evidence Record can embed the same inspector component, but the Evidence Record has additional citation and claims metadata.

## 12. Methodology Page

The methodology page must include:

- severity taxonomy
- deterministic rule matching
- `*` / `**` JSON Pointer glob semantics
- timing modifier
- value signals
- rule set hash
- critical-density denominator
- per-patch vs per-trial distributions
- power-law amendment distribution
- single-indication limitation
- `/api/int` durability risk
- whyStopped regulatory context
- post-completion endpoint-change external evidence
- competition / positioning disclosure

## 13. Case Studies

### Case A: NCT05094102

Purpose: clean structural demonstration of primary outcome change detection.

Public framing:

> This is a methodology example of a detectable material amendment. It is not presented as evidence of wrongdoing.

### Case B: NCT01275677

Purpose: post-completion secondary outcome / results-outcome modification.

Public framing:

> Post-completion modifications can have legitimate explanations including manuscript preparation, regulatory feedback, or data cleaning. This Evidence Record is surfaced for review priority, not as an indication of irregularity.

### Evidence Record requirement

Both case studies should link to their Amendment Evidence Records and display the citation block.

## 14. Citation Block

Every Evidence Record page should include a copyable citation:

```text
TrialDiff Evidence Record evt_NCT01275677_v23_v24_a3f2b1c0.
Coordination Science Institute. Generated 2026-05-21.
https://trialdiff.org/events/evt_NCT01275677_v23_v24_a3f2b1c0
```

For flagship curated case studies, consider Zenodo DOI publication later. Do not mint DOIs for every event in v1.1.

## 15. v1.1 Definition of Done

### Pipeline

- [x] Harvester stores official v2 snapshots
- [x] Harvester stores `/api/int` histories and adjacent JSON Patches
- [x] Classifier deterministic and idempotent
- [x] Rule set hash stored
- [x] `classify --force` supports recalibration
- [ ] Neon migration completed
- [ ] GitHub Actions cron writes to Neon
- [ ] Evidence Record view/query derives stable `event_id`
- [ ] Canonical Evidence Record JSON generated for high/critical events

### Frontend

- [x] Astro SSR scaffold
- [x] Raw SQL query layer
- [x] Trial detail page
- [x] Server-rendered patch inspector implemented
- [ ] Four homepage lenses, including post-completion material edits
- [ ] Evidence Record page `/events/{event_id}`
- [ ] Evidence Record canonical JSON `/events/{event_id}.json`
- [ ] Citation block
- [ ] Claims supported / claims not supported display
- [ ] Methodology page updated with v1.1 disclosures
- [ ] Case Study A page
- [ ] Case Study B page
- [ ] README updated with competition / positioning disclosure

### Methodology

- [x] 25-study calibration documented
- [x] 100-study calibration documented
- [x] dual-distribution finding documented
- [ ] external commercial-monitoring landscape acknowledged
- [ ] JAMA endpoint-change comparator cited
- [ ] whyStopped legal context cited
- [ ] results-clock context explained

## 16. Out of Scope for v1.1

- Sponsor-facing private portfolio monitoring
- Email/SMS alerting
- Subscription product
- User accounts
- Multi-indication corpus expansion
- CTIS ingestion
- Atlas views
- Legal compliance scoring
- Sponsor reputation scoring
- LLM-driven severity
- DOI minting for every event

## 17. Phase 2 Roadmap

### TrialDiff Atlas

Deferred Phase 2 direction:

> A temporal atlas of how clinical trial design spaces evolve across indications.

The atlas should aggregate amendment patterns across indications:

- endpoint convergence/divergence
- comparator arm migration
- timeline drift distributions
- eligibility broadening/narrowing
- amendment burden by design family
- post-completion material edit rates

The atlas requires normalization layers not needed for v1.1:

- indication ontology
- intervention class normalization
- endpoint clustering
- comparator taxonomy
- biomarker / line-of-therapy context

### CTIS / EU expansion

EMA's revised CTIS transparency rules provide a credible Phase 2 cross-jurisdiction path. The CTIS public portal and revised transparency rules became applicable on 18 June 2024 and cover structured publication across trial lifecycle events including substantial modifications, early termination, temporary halt, restart, serious breaches, urgent safety measures, and results timing.

Sources:

- [EMA revised CTIS transparency rules](https://www.ema.europa.eu/system/files/documents/other/revised_ctis_transparency_rules_en.pdf)
- [European Commission Clinical Trials Regulation](https://health.ec.europa.eu/medicinal-products/clinical-trials/clinical-trials-regulation-eu-no-5362014_en)

## 18. Public Positioning Copy

Recommended README / methodology copy:

> TrialDiff is not a private watchlist or commercial pipeline-intelligence dashboard. Commercial tools already provide sponsor-oriented trial-change alerts. TrialDiff's purpose is different: to create an open, reproducible amendment evidence layer for public-interest research, journalism, and methodological review.

Required persistent disclaimer:

> Severity means review priority, not proven wrongdoing.

Required Evidence Record disclaimer:

> This record supports claims about what changed in the public registry record and how TrialDiff classified that change. It does not support claims about sponsor intent, scientific justification, regulatory violation, or trial outcome impact.

## 19. What Changed From v1.0

- Replaced broad market-gap claim with open evidence-layer positioning.
- Added Amendment Evidence Record as first-class v1.1 artifact.
- Added deterministic public event ID scheme.
- Added claims-supported / claims-not-supported requirement.
- Added citation block requirement.
- Added post-completion material edits as fourth homepage lens.
- Added JAMA endpoint-change paper as external empirical context.
- Reframed `whyStopped` using 42 CFR § 11.64.
- Added results-clock context as orientation, not compliance scoring.
- Updated architecture to server-rendered patch inspector with no React requirement.
- Added competition / positioning disclosure for README and methodology.

---

*TrialDiff v1.1 ships when Section 15 is complete. The Phase 2 atlas remains explicitly deferred.*
