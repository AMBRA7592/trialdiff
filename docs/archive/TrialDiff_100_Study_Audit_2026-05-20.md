# TrialDiff 100-Study Corpus Audit

> **Archived historical audit (2026-05-20).** Describes the FIRST 100-study corpus snapshot (4,479 patches / 864 events under pre-tightening rules), whose SQLite file later became unreadable. The live deployment uses the regenerated snapshot (4,485 patches / 868 events under v0.2.1 rules) — see `../../CORPUS.md` for the reconciliation. Severity framing herein was retracted; see `../../SEVERITY_DECOUPLING_v0.2.1.md`. The dual-distribution finding (patch volume vs critical density) stands.

**Date:** 2026-05-20
**Corpus:** `breast_cancer_phase2_3_20260520_limit100`
**Database:** `trialdiff_breast_cancer_limit100.sqlite3`

## Summary

The 100-study breast cancer corpus validates the core classifier architecture and surfaces a methodological finding that should shape both reporting and frontend design:

> Patch volume and critical-event density are different axes.

Large amendment-volume trials are not necessarily the trials with the highest critical density. The highest-density trials are often smaller studies where a high fraction of amendments materially alter outcomes, interventions, enrollment, design, or major timeline expectations.

## Corpus Shape

- Studies selected: 100
- Candidate records scanned: 800
- Locally eligible before history filter: 139
- Selector errors: 0
- Adjacent patches ingested: 4,479
- Materiality events after calibration and adverse-events rule slice: 864
- Missing pre-amendment records during classification: 0

Patch volume is highly concentrated:

| NCT ID | Patches |
|---|---:|
| NCT00769379 | 1,650 |
| NCT01275677 | 979 |
| NCT00490139 | 202 |
| NCT01124695 | 131 |
| NCT01224678 | 111 |

The top 2 trials account for 58.7% of patch volume. The top 5 account for 68.6%.

## Per-Patch Distribution

| Severity | Events | % of All Patches |
|---|---:|---:|
| Critical | 367 | 8.2% |
| High | 310 | 6.9% |
| Medium | 69 | 1.5% |
| Low | 118 | 2.6% |
| Unclassified | 3,615 | 80.7% |

Among classified events only:

| Severity | Events |
|---|---:|
| Critical | 367 |
| High | 310 |
| Medium | 69 |
| Low | 118 |

## Per-Trial Distribution

| Metric | Mean | Median |
|---|---:|---:|
| Patches per trial | 44.79 | 10 |
| Materiality events per trial | 8.64 | 7 |
| Critical events per trial | 3.67 | 2 |
| High events per trial | 3.10 | 3 |

This median view is the more honest answer to "what does a typical trial look like?" The corpus-wide per-patch view answers a different question: "what does the full amendment stream contain?"

## Critical Event Concentration

| Group | Critical Events | Share |
|---|---:|---:|
| Top 5 trials by critical count | 95 / 367 | 25.9% |
| Top 10 trials by critical count | 139 / 367 | 37.9% |

High patch volume does not imply high critical density:

| NCT ID | Patches | Critical | High |
|---|---:|---:|---:|
| NCT00769379 | 1,650 | 31 | 4 |
| NCT01275677 | 979 | 23 | 6 |

Highest critical-density trials, restricted to trials with at least 10 patches:

| NCT ID | Patches | Critical | Critical Rate | Title |
|---|---:|---:|---:|---|
| NCT00165256 | 17 | 12 | 70.59% | Wide Excision Alone as Treatment for Ductal Carcinoma in Situ of The Breast |
| NCT03094169 | 13 | 8 | 61.54% | AVID100 in Advanced Epithelial Carcinomas |
| NCT00629616 | 11 | 6 | 54.55% | Efficacy of Anastrozole and Fulvestrant in Patients With ER Positive, HER2 Negative, Operable Breast Cancer |

These are stronger case-study candidates than the highest patch-volume trials.

## Calibration Changes From Audit

Two narrow classifier fixes were made after the 100-study audit:

1. `ESTIMATED` or `ANTICIPATED` date changed to earlier `ACTUAL` date now classifies as `timeline_actualized_earlier` with low severity.
2. `reviewUnit` metadata under protocol outcome records no longer triggers outcome-change rules by itself.
3. Results adverse-event rules now classify serious adverse event additions/modifications, serious adverse event removals, other adverse-event changes, and adverse-event group denominator/count changes.

After reclassification:

- Events changed from 861 to 864 after adding the adverse-events rule slice.
- Earlier actualized date events now appear as low-severity timeline metadata.
- `reviewUnit`-only outcome metadata no longer creates a materiality event.
- Tests increased to 32 and pass.

## Timing Modifier

Timing escalation after the fixes:

| Timing Context | Escalated | Total |
|---|---:|---:|
| Early recruitment | 0 | 410 |
| Late recruitment | 73 | 272 |
| Post recruitment | 8 | 65 |
| Pre recruitment | 0 | 117 |

Escalation breakdown:

| Category | Timing | Base | Final | Count |
|---|---|---|---|---:|
| timeline_major_slip | late_recruitment | high | critical | 39 |
| enrollment_change | late_recruitment | high | critical | 26 |
| secondary_outcome_change | late_recruitment | high | critical | 6 |
| secondary_outcome_change | post_recruitment | high | critical | 6 |
| eligibility_change | late_recruitment | high | critical | 2 |
| enrollment_change | post_recruitment | high | critical | 1 |
| timeline_major_slip | post_recruitment | high | critical | 1 |

## Post-Recruitment Secondary Outcome Audit

Six post-recruitment secondary-outcome escalations were reviewed:

- `NCT00128856` appears mostly punctuation/wording cleanup, with one abbreviation expansion.
- `NCT01275677` removes a secondary outcome and corresponding result outcome measures after completion. This is a strong manual-review candidate.
- `NCT05243641` has three events after termination:
  - One substantive narrowing of adverse-event secondary-outcome description to "phase II patients."
  - One now-suppressed review metadata-only event.
  - One time-frame change from "up to 3 years" to "up to 27 months."
- `NCT05415215` includes secondary-outcome time-frame shortening and scale-description rewrites after completion.

These should remain human-review events. They are not all suspicious, but they are exactly the kind of post-results/post-completion changes TrialDiff should surface with careful framing.

Recommended frontend copy for post-completion outcome changes:

> This trial's outcome, time frame, or outcome description was modified after the study reached completed or terminated status. Post-completion modifications can have legitimate explanations including manuscript preparation, regulatory feedback, or data cleaning. This event is surfaced for review priority, not as an indication of irregularity.

`NCT01275677` is the strongest post-completion case surfaced so far. It removes a secondary outcome and corresponding result outcome measures after completion. This should be treated as Case Study B, paired with `NCT05094102` as Case Study A for the structural in-trial outcome-change demonstration.

## Coverage Gaps

Unclassified operations are dominated by administrative paths:

| Bucket | Ops |
|---|---:|
| location metadata | 36,689 |
| registry housekeeping | 7,940 |
| other | 248 |
| sponsor/collaborator | 39 |
| other results section | 29 |
| non-terminal overall status | 15 |
| description text | 15 |
| results adverse events | 3 |

The adverse-events rule slice reduced unclassified adverse-event operations from 485 to 3.

New adverse-event categories in the 100-study corpus:

| Severity | Category | Events |
|---|---|---:|
| High | serious_adverse_event_addition | 2 |
| High | serious_adverse_event_modification | 1 |
| High | adverse_event_group_change | 1 |

No serious adverse-event removals appeared in this corpus. The critical rule is present for future runs because removal of reported serious adverse-event data is structurally high-stakes.

## Frontend Implication

Default sorting should not be "most amended." It should expose three explicit lenses:

1. **Patch volume / amendment intensity**: activity and administrative churn.
2. **Critical density**: consequentiality and review priority.
3. **Recent material activity**: most recent critical/high events across a rolling 30- or 90-day window.

The first screen should let users move between corpus-wide patch/event distribution and per-trial review priority. A high-volume, low-density platform trial and a low-volume, high-density focused trial are different phenomena and should not compete on one undifferentiated ranking.

A persistent disclaimer should appear across all frontend views:

> Severity means review priority, not proven wrongdoing.
