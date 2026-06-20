# TrialDiff v0.2.1 Severity Re-Certification

Status: failed calibration gate; buyer-facing brief remains blocked.

This document records the v0.2.1 re-certification pass after diagnostic rule
tightening and rubric-boundary clarification. The re-certification used an
expanded 100-study breast-cancer corpus and a fresh blinded sample not used for
the v0.2 diagnostic tuning loop.

## Frozen Inputs

- Scope: `V0.2_SCOPE.md`
- Diagnostic plan: `V0.2.1_DIAGNOSTIC_PLAN.md`
- Disagreement analysis: `V0.2.1_DISAGREEMENT_ANALYSIS.md`
- Rule tightening diagnostic: `V0.2.1_RULE_TIGHTENING_DIAGNOSTIC.md`
- Rubric revision note: `V0.2.1_RUBRIC_REVISION_NOTE.md`
- Rubric: `SEVERITY_RUBRIC_v0.2.md`, refined and re-frozen at commit `51befbf`
- Sample manifest: `CALIBRATION_SAMPLE_v0.2.1.csv`
- Blinded review package: `CALIBRATION_REVIEW_PACKAGE_v0.2.1.jsonl`
- Private crosswalk: `CALIBRATION_REVIEW_CROSSWALK_PRIVATE_v0.2.1.csv`
- Scorer: `scripts/score_calibration_reviews.py`

## Disclosure

The v0.2.1 rubric was refined after inspection of the v0.2 calibration
disagreements and with visibility into TrialDiff classifier behavior. The
v0.2.1 classifier rules were likewise revised against the seen v0.2 diagnostic
sample; certification therefore requires records not used in that diagnostic.

This is not a fully independent reference standard. The supported independence
claim is limited to blinded fresh-context application of the refined rubric to
fresh records.

## Expanded Corpus

The v0.2.1 corpus was regenerated outside the iCloud-backed workspace from
`corpora/breast_cancer_phase2_3_20260520_limit100.txt`.

Derived event counts under the v0.2.1 rules:

- materiality events: 868
- evidence records: 483
- critical: 87
- high: 396
- medium: 217
- low: 168

## Sample

The fresh re-certification sample contains 91 records:

- 30 critical
- 30 high
- 11 medium
- 20 low

The sample was drawn with seed `trialdiff-v0.2.1-recert-2026-06-18`.

The review package was shuffled with seed
`trialdiff-v0.2.1-review-package-2026-06-18`.

## Review Mechanism

Two fresh reviewer contexts independently applied the refined rubric to the
blinded review package.

The package hid TrialDiff severity, category, deterministic rules fired,
evidence record IDs, and derived timing labels. Reviewers saw neutral record
IDs, changed paths, patch payloads with old values reconstructed, raw
FROM-version status fields, and provenance.

Reviewer outputs:

- Reviewer 1: `CALIBRATION_REVIEWER_1_v0.2.1.jsonl`
- Reviewer 2: `CALIBRATION_REVIEWER_2_v0.2.1.jsonl`

## Results

Reviewer 1 distribution:

- critical: 18
- high: 17
- medium: 12
- low: 43
- insufficient evidence: 1

Reviewer 2 distribution:

- critical: 4
- high: 19
- medium: 13
- low: 55

### Critical Tier

Reviewer 1 confirmed 17 of 30 TrialDiff-critical records as critical.

- Not confirmed as critical: 13 / 30
- Downgrade rate: 43.3%

Reviewer 2 confirmed 4 of 30 TrialDiff-critical records as critical.

- Not confirmed as critical: 26 / 30
- Downgrade rate: 86.7%

This fails the critical-tier calibration gate.

### Combined Critical + High Tier

Reviewer 1 reviewed 27 of 60 TrialDiff critical/high records as below high.

- Below high: 27 / 60
- Downgrade rate: 45.0%

Reviewer 2 reviewed 38 of 60 TrialDiff critical/high records as below high.

- Below high: 38 / 60
- Downgrade rate: 63.3%

This fails the combined critical+high calibration gate.

## Interpretation

The v0.2.1 tightening improved the visible critical pool size and preserved
results-reconciliation records rather than erasing them, but it did not produce
a calibrated upper-priority standard under fresh blinded review.

The remaining failure is concentrated in upper-tier assignment, especially
critical primary-outcome and high-priority categories that reviewers often
downgraded to medium or low. Reviewer 1 is less strict than Reviewer 2, but both
fail the pre-registered gates.

## Consequences

The buyer-facing brief remains blocked.

The current record should be treated as a useful failed calibration cycle:

1. The evidence-record primitive held: stable IDs, source links, hashes,
   provenance, claim boundaries, sample manifests, and blinded review mechanics
   all functioned.
2. The severity standard remains uncalibrated for external high-priority use.
3. Further rule tightening should not be tuned against this v0.2.1 sample as if
   it were certifying data. Any next certification pass requires another fresh
   sample or an explicitly held-out stratum.

## Critical-Stratum Adjudication Addendum

After the failed v0.2.1 pass, additional fresh-context applications of the rubric were run over the full 30-record TrialDiff-critical stratum. Across usable fresh applications, critical confirmations were 4/30, 5/30, 12/30, and 17/30.

The pre-registered critical gate required at least 24/30 confirmations. No application came close to that threshold. The spread also shows that the critical review-priority boundary was not stable enough to serve as a validated reference standard in this design.

This converts the next step from another rule-tightening cycle to decoupling: severity remains deterministic uncalibrated triage metadata, and the citable Evidence Record primitive continues without a certified-severity claim. See `SEVERITY_DECOUPLING_v0.2.1.md`.

## Non-Claims

This re-certification does not establish:

- that any sponsor acted improperly;
- that any trial amendment was scientifically unjustified;
- that manuscript disclosure was absent;
- that TrialDiff has been externally clinically validated;
- that the evidence-record format failed;
- that the current v0.2.1 severity labels are suitable for a buyer-facing
  high-priority brief;
- that the current severity labels are validated review-priority judgments.

The supported conclusion is limited to severity calibration: v0.2.1 still
over-fires at the upper tiers under blinded fresh-context model review, and
severity should be treated as deterministic uncalibrated triage metadata.
