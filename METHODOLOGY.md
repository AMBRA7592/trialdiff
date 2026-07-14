# TrialDiff — Documentation Map and Reading Order

This repository accumulated its documentation as a working paper trail. This
file is the map: what each document is, whether it is current, and the order
a first-time reader should take.

## Start here (the current state)

| Order | Document | What it is |
| --- | --- | --- |
| 1 | `README.md` | What TrialDiff is, what is deployed, how to verify the frozen packages |
| 2 | `CLAIMS.md` / `NON_CLAIMS.md` | The exact claim boundary: what the artifact asserts and refuses to assert |
| 3 | `EVIDENCE_RECORD_PRIMITIVE.md` | The domain-general primitive: deterministic, claim-bounded, hash-verifiable records |
| 4 | `VALIDATION.md` | Validation and audit status of the frozen v0.1-alpha package |
| 5 | `ERRATA.md` | Known defects in published artifacts and the manifest re-pin policy |
| 6 | `VERSIONS.md` | Untangles the four version lines (specs, releases, calibration, event-class packages) |
| 7 | `CORPUS.md` | Which corpora exist and how their counts reconcile |
| 8 | `DATA_DICTIONARY.md` | Both record schemas, field by field, and how they evolved |

## The severity calibration arc (why severity is "uncalibrated triage metadata")

Read in this order — it is a pre-registered attempt to validate severity as
review priority, its failure, a diagnostic cycle, a second failure, and the
decision to stop:

1. `V0.2_SCOPE.md` — the calibration's scope and gate (< 20% critical false-positive rate)
2. `SEVERITY_RUBRIC_v0.2.md` — the frozen review rubric
3. `CALIBRATION_SAMPLE_PLAN_v0.2.md` — blinded, stratified sample design
4. `SEVERITY_CALIBRATION_v0.2.md` — first result: 6/30 and 3/30 critical confirmations → gate failed
5. `V0.2.1_DIAGNOSTIC_PLAN.md` — the planned diagnostic (no tuning on the burned sample)
6. `V0.2.1_DISAGREEMENT_ANALYSIS.md` — split labeling: rubric gap vs judgment variance vs reviewer error
7. `V0.2.1_RULE_TIGHTENING_DIAGNOSTIC.md` — rule changes (critical 35→8 on the alpha corpus; blanket timing escalation disabled)
8. `V0.2.1_RUBRIC_REVISION_NOTE.md` — the re-frozen rubric boundaries
9. `SEVERITY_CALIBRATION_v0.2.1.md` — re-certification result: 17/30 and 4/30 → gate failed again
10. `V0.2.1_REVIEWER_SPLIT_ANALYSIS.md` — both reviewers unanimously downgraded 13/30 criticals
11. `SEVERITY_DECOUPLING_v0.2.1.md` — the decision: severity stays deterministic, uncalibrated metadata; the buyer-facing priority claim is retired

Supporting data for the arc (root `CALIBRATION_*` files): reviewer outputs,
blinded review packages, samples, and the unblinding-key crosswalks. These
are anchored by `MANIFEST.calibration.sha256`.

## The data packages

| Package | Status | Contents |
| --- | --- | --- |
| `records/` | Frozen (v0.1-alpha) | 40 selected high/critical Evidence Records from the 25-study alpha corpus; pinned by `MANIFEST.sha256` |
| `event_class_records_v0.1/` | Historical stub | Superseded by v0.1.1 (records were byte-identical; see the stub README) |
| `event_class_records_v0.1.1/` | Frozen, with erratum | 100 event-class Evidence Records over 52 trials; see `ERRATA.md` E1 for the whyStopped class defect |

## Historical strategy documents (archived)

`docs/archive/` holds the pre-calibration working documents. They are kept
for the record and carry banners: their severity framing ("severity means
review priority") was retracted by the calibration outcome.

- `TrialDiff_Wild_Scout_Memo_2026-05-19.md` — the original technical unlock (undocumented CT.gov history endpoints)
- `TrialDiff_Product_Spec_v0.2.md`, `_v0.3.md`, `_v1.1.md` — product specs; v1.1 is the most ambitious and the most retracted
- `TrialDiff_100_Study_Audit_2026-05-20.md` — the first 100-study corpus audit
- `TrialDiff_Breast_Cancer_Corpus_Plan.md` — the reproducible corpus selector definition

## Tooling

- `trialdiff verify <record.json|dir>` — offline integrity verification of any exported record
- `scripts/validate_alpha_demo.py` — frozen alpha package validator (recomputes hashes)
- `scripts/validate_event_class_package.py` — event-class package validator (manifest, canonical form, expected stats)
- `scripts/seed_from_records.py` — build a runnable local database from the committed records
- `RELEASING.md` — operator runbook for regeneration, deployment, and freezing new packages
