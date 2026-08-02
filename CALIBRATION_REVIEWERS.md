# Calibration Reviewer Provenance

What is and is not known about the reviewers behind the v0.2/v0.2.1
severity-calibration results. This note exists because a reference standard
is only as credible as its provenance, and parts of this one were
under-recorded at review time.

## Design (pre-registered)

`CALIBRATION_SAMPLE_PLAN_v0.2.md` §6 fixed the reviewer mechanism before
any record was reviewed: **fresh-context model review against the frozen
rubric** (`SEVERITY_RUBRIC_v0.2.md`, commit `a764e33`; revised boundaries
re-frozen at `51befbf` for v0.2.1). Each reviewer had to be a model
instance with no exposure to TrialDiff's severity labels, categories,
rules, value signals, or timing labels, receiving only the blinded inputs
defined in §5. The plan explicitly allows a later human domain-expert pass
to be reported separately; none has been run.

## What is filed (verifiable)

| Application | Result (critical confirmations) | Output file |
| --- | --- | --- |
| v0.2 Reviewer 1 | 6/30 | `CALIBRATION_REVIEWER_1_v0.2.jsonl` |
| v0.2 Reviewer 2 | 3/30 | `CALIBRATION_REVIEWER_2_v0.2.jsonl` |
| v0.2.1 Reviewer 1 | 17/30 | `CALIBRATION_REVIEWER_1_v0.2.1.jsonl` |
| v0.2.1 Reviewer 2 | 4/30 | `CALIBRATION_REVIEWER_2_v0.2.1.jsonl` |

Scoring is reproducible from these files plus the unblinding keys via
`scripts/score_calibration_reviews.py`.

## What is prose-only (known gap)

The critical-stratum adjudication addendum in
`SEVERITY_CALIBRATION_v0.2.1.md` reports four fresh applications over the
30-record critical stratum: 4/30, 5/30, 12/30, 17/30. Two of those numbers
coincide with the filed v0.2.1 reviewer results; **no separately named
output files were committed for the additional applications**. Their
inputs exist (`CALIBRATION_REVIEW_CRITICAL_STRATUM_ADJUDICATION_PACKAGE_v0.2.1.jsonl`),
their per-record outputs do not. Treat the 5/30 and 12/30 figures as
reported-but-not-independently-replayable.

## What was never recorded (known gap)

The **model identity, version, and provider** of the reviewer instances
were not recorded at review time, nor was the context-initialization
procedure beyond the plan's exposure constraints. This cannot be
reconstructed after the fact and is stated here as a limitation of the
v0.2/v0.2.1 evidence rather than papered over.

Interpretive consequence: the calibration outcome should be read as "the
deterministic rules over-fire at the upper tiers under blinded fresh-context
model review, and the critical boundary was unstable across such
applications" — a negative result about TrialDiff's severity labels under
this review design, not a validated human-expert standard.

## Requirements for any future round

1. Record reviewer provenance per application: model/version/provider (or
   human reviewer role/affiliation), initialization procedure, and date.
2. Commit one named output file per application — including adjudication
   passes — before computing any aggregate.
3. Keep unblinding keys sealed until the round closes
   (commit–reveal: `RELEASING.md` §E).
