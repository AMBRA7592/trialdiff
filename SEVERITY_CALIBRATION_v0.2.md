# TrialDiff v0.2 Severity Calibration

Status: failed calibration gate; buyer-facing brief blocked pending rule revision.

This document records the first v0.2 severity-calibration pass for the TrialDiff
25-study alpha corpus. It evaluates whether TrialDiff's deterministic severity
labels are defensible as review-priority labels under the frozen v0.2 rubric.

## Frozen Inputs

- Scope: `V0.2_SCOPE.md`
- Rubric: `SEVERITY_RUBRIC_v0.2.md`, frozen at commit `a764e33`
- Sample plan: `CALIBRATION_SAMPLE_PLAN_v0.2.md`
- Sample manifest: `CALIBRATION_SAMPLE_v0.2.csv`
- Blinded review package: `CALIBRATION_REVIEW_PACKAGE_v0.2.jsonl`
- Private crosswalk: `CALIBRATION_REVIEW_CROSSWALK_PRIVATE_v0.2.csv`
- Scorer: `scripts/score_calibration_reviews.py`

The review package hid TrialDiff severity, category, deterministic rules fired,
evidence record IDs, and derived timing labels. Reviewers saw neutral record IDs,
changed paths, patch payloads with old values reconstructed, raw FROM-version
status fields, and provenance. The private crosswalk was used only after review.

## Review Mechanism

This calibration used adversarial model review against a frozen rubric. It is not
external clinical-domain validation. The review mechanism should be described as
independent blinded model review, not as expert clinical adjudication.

Two fresh reviewer contexts independently applied `SEVERITY_RUBRIC_v0.2.md` to
the 91-record blinded package:

- Reviewer 1 output: `CALIBRATION_REVIEWER_1_v0.2.jsonl`
- Reviewer 2 output: `CALIBRATION_REVIEWER_2_v0.2.jsonl`

## Sample

The sample contains 91 records:

- 30 critical
- 30 high
- 11 medium
- 20 low

The critical and high strata are the threshold-gated tiers. Medium is a forced
census of the 25-study corpus and is directional rather than rate-powered.

## Pre-Registered Gate

The v0.2 scope pre-registered the calibration gate:

- Critical false-positive / downgrade rate must be below the stated critical
  threshold.
- Combined critical+high false-positive / downgrade rate must be below the
  stated combined threshold.
- No whole category may be systematically mis-tiered where the sample has enough
  records to evaluate that category.

The buyer-facing brief is blocked if the calibration gate fails.

## Results

Reviewer 1 distribution:

- critical: 6
- high: 34
- medium: 16
- low: 35

Reviewer 2 distribution:

- critical: 3
- high: 16
- medium: 27
- low: 45

### Critical Tier

Reviewer 1 confirmed 6 of 30 TrialDiff-critical records as critical.

- Not confirmed as critical: 24 / 30
- Downgrade rate: 80.0%

Reviewer 2 confirmed 3 of 30 TrialDiff-critical records as critical.

- Not confirmed as critical: 27 / 30
- Downgrade rate: 90.0%

This fails the critical-tier calibration gate.

### Combined Critical + High Tier

Reviewer 1 reviewed 20 of 60 TrialDiff critical/high records as below high.

- Below high: 20 / 60
- Downgrade rate: 33.3%

Reviewer 2 reviewed 41 of 60 TrialDiff critical/high records as below high.

- Below high: 41 / 60
- Downgrade rate: 68.3%

This fails the combined critical+high calibration gate.

## Category Signals

The strongest recurring over-prioritization signal is `timeline_significant_shift`.

For TrialDiff critical/high records:

- Reviewer 1: `timeline_significant_shift` had 16 records; 12 were reviewed as
  medium or low.
- Reviewer 2: `timeline_significant_shift` had 16 records; all 16 were reviewed
  as medium or low.

Other important signals:

- Primary outcome changes remain the strongest candidate critical family, but
  not all primary-outcome text edits survived blinded review as critical.
- Results-reconciliation-like outcome edits were commonly down-weighted.
- Large timeline movements during active recruitment were often reviewed as
  medium unless the rubric's late-stage or interpretability criteria were met.
- Terminal-status records with present but business-like `whyStopped` text were
  generally reviewed as high, not critical.
- Medium and low strata behaved as expected: all 11 TrialDiff-medium records were
  reviewed as low by both reviewers; 19 of 20 TrialDiff-low records were reviewed
  as low by both reviewers, with one reviewed as medium.

## Interpretation

This is not evidence that TrialDiff's amendment detection is invalid. The
calibration failure is narrower:

TrialDiff v0.1/v0.2 over-assigns the upper review-priority tiers, especially the
critical tier and timeline-significant high tier.

The evidence-record primitive remains useful: records are reproducible,
source-linked, hash-backed, and claim-bounded. What does not yet hold is the
claim that the current severity labels are calibrated enough for a buyer-facing
high-priority brief.

## Consequences

The v0.2 buyer-facing brief is blocked.

The next v0.2 engineering/research step is rule tightening, not corpus expansion
or UI work:

1. Rework critical escalation rules so critical is reserved for changes that
   materially alter primary evidence interpretation, terminal-status
   interpretability, or similarly high-stakes review questions.
2. Down-tier `timeline_significant_shift` unless it meets late-stage,
   completion-proximate, or independently large-magnitude criteria.
3. Add explicit results-reconciliation suppression for outcome text changes
   co-incident with results-section population or `hasResults` transition.
4. Clarify whether very large timeline slips during active recruitment should
   have a separate high-priority magnitude override.
5. Re-run evidence generation under a new `rule_set_hash`, preserving v0.1 as a
   frozen artifact rather than rewriting its history.

## Non-Claims

This calibration does not establish:

- that any sponsor acted improperly;
- that any trial amendment was scientifically unjustified;
- that manuscript disclosure was absent;
- that TrialDiff has been externally clinically validated;
- that the evidence-record format failed;
- that TrialDiff should expand corpus scope before rule revision.

The supported conclusion is limited to severity calibration: the current
review-priority labels over-fire at the upper tiers under blinded adversarial
model review.
