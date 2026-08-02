# Corpora

TrialDiff's published numbers come from several corpus snapshots. This file
pins what each corpus is, which artifacts it produced, and reconciles the
count discrepancies a careful reader will notice across documents.

## Selector

All corpora use the reproducible selector defined in
`docs/archive/TrialDiff_Breast_Cancer_Corpus_Plan.md`: interventional
breast-cancer-related studies, Phase 2/3, at least 3 registry versions,
updated within the trailing window, ordered deterministically. The selected
NCT lists are committed under `corpora/`:

- `breast_cancer_phase2_3_20260520_limit25.{json,txt}` — 25-study list
- `breast_cancer_phase2_3_20260520_limit100.{json,txt}` — 100-study list

The lists are frozen inputs; ingest against today's live ClinicalTrials.gov
API can differ (new versions get added over time), which is why derived
counts are always quoted per snapshot.

## Snapshot A — 25-study alpha corpus (v0.1-alpha, frozen 2026-06-17)

- 25 trials, 280 adjacent patches, 122 materiality events, 86 Evidence Records
- 40 selected high/critical records exported to `records/` and pinned by `MANIFEST.sha256`
- Rule generation: v0.1-alpha rules (pre-tightening); 7 of the 40 exported records show timing escalation (`severity != severity_pre_timing`)

## Snapshot B — first 100-study corpus (audited 2026-05-20, later unreadable)

- 100 trials, **4,479** adjacent patches, **864** materiality events
  (367 critical / 310 high / 69 medium / 118 low under pre-tightening rules)
- Documented in `docs/archive/TrialDiff_100_Study_Audit_2026-05-20.md`
- The SQLite file became unreadable before the alpha freeze (the reason the
  alpha shipped as a 25-study demo). Its numbers survive only in that audit

## Snapshot C — regenerated 100-study corpus (2026-06-18, current)

- 100 trials, **4,485** adjacent patches, **868** materiality events
  (87 critical / 396 high / 217 medium / 168 low under v0.2.1 tightened rules)
- An intermediate, pre-membership generation emitted **483** records under
  the older materiality-filter inclusion policy
- The event-class v0.1/v0.1.1 generation emitted **100** records over 52
  trials; those bytes are published but carry erratum E1
- Corrected generation from this exact frozen snapshot emits **97** records
  over 54 trials under the v0.2 definitions; this is the required v0.1.2
  release population
- Source of: the v0.2.1 calibration sample, the published event-class
  packages, and the live deployment at trialdiff.vercel.app

## Reconciling the discrepancies

- **4,479 vs 4,485 patches; 864 vs 868 events** (Snapshot B vs C): the two
  100-study ingests ran a month apart against the live registry; trials
  amended in between contributed additional adjacent version pairs. The
  corpus *selector list* is identical; the *registry contents* moved.
- **367 vs 87 critical events**: not corpus drift — the v0.2.1 rule
  tightening (`V0.2.1_RULE_TIGHTENING_DIAGNOSTIC.md`) deliberately reduced
  critical firing (on the 25-study corpus: 35 → 8).
- **86 vs 483 vs 100/97 Evidence Records**: 86 is the alpha's complete
  severity-selected population (40 exported); 483 is the intermediate
  materiality-filter population; 100 is the published v0.1.1 event-class
  population; 97 is the corrected v0.1.2 event-class population. The last
  two use membership-driven inclusion, and their difference is erratum E1.
- **25-study vs 100-study trial overlap**: the two selected lists share only
  1 NCT ID — the limit-25 and limit-100 runs are different slices of the
  ranked candidate pool, not a subset relationship. The 40 frozen alpha
  records and the 100 event-class records consequently share no events.
