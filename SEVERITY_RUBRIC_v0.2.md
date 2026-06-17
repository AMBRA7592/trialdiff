# Severity Rubric - TrialDiff v0.2 Calibration

Status: DRAFT - not yet frozen. Must be pressure-tested for independence and committed before any calibration sample is drawn or reviewed.
Date: 2026-06-18
Applies to: TrialDiff v0.2 severity calibration (see `V0.2_SCOPE.md` Sections 4-5)

## Purpose

This rubric defines review priority for a single ClinicalTrials.gov registry change: one adjacent version-to-version patch. It is designed to be applied independently of how the TrialDiff classifier assigns severity.

Review priority means: how much a careful reader concerned with trial integrity, interpretability, or participant safety would want to examine this change.

It is not a judgment of wrongdoing, misconduct, intent, manuscript disclosure, clinical merit, or regulatory compliance.

## Independence And Provenance Note

This draft was authored after parts of TrialDiff's classifier design were already known in the project conversation, including change categories, timing escalation, and several value-signal patterns. That means this rubric is not fully independent of the classifier it is meant to test.

Before freezing, do one of the following, in descending order of strength:

1. Have a reviewer or model with no exposure to TrialDiff classifier internals independently re-derive the rubric from the purpose statement above.
2. Have a fresh reviewer or model apply this rubric in stage 1, without seeing TrialDiff's assigned severity, category, or rules fired.
3. At minimum, pressure-test every tier boundary below against review-priority reasoning alone, and adjust anything that appears inherited from the classifier rather than derived from the review-priority purpose.

`SEVERITY_CALIBRATION_v0.2.md` must state which independence path was used. It must not describe the result as more independent than it was.

## Stage 1 Reviewer Inputs

During stage 1, the reviewer sees only raw or source-derived material:

- changed JSON Pointer paths;
- patch operations and new values;
- reconstructed old values from the FROM-version snapshot where needed;
- FROM-version recruitment/status fields needed to derive timing context;
- source URLs;
- hashes;
- version numbers.

The reviewer does not see:

- TrialDiff's assigned severity;
- TrialDiff's category label;
- TrialDiff's rules fired;
- TrialDiff's timing-context label;
- any TrialDiff-generated explanatory summary.

The reviewer derives timing context from the FROM-version registry status fields rather than accepting TrialDiff's derived timing label.

## Core Decision Procedure

Apply in order:

1. Characterize the change in one sentence from the changed paths and values, for example: "primary outcome measure text replaced," "overall status changed to terminated and whyStopped is empty," or "primary completion date moved later by about two years."
2. Check for results-reconciliation co-incidence. If the patch also sets `/hasResults` true or adds `/resultsSection`, treat co-incident outcome-field text changes as presumptive results-posting or results-reconciliation changes, not prospective outcome changes, unless the payload shows a substantive independent change. Down-weight reconciliation-only changes to administrative or low.
3. Derive timing context from the FROM-version registry status fields: before recruitment, recruiting, active/not-recruiting, completed, terminated, withdrawn, suspended, or unknown.
4. Assign a base tier from the change type criteria below.
5. Apply timing escalation where applicable.
6. For multi-change patches, the record's tier is the highest tier justified by any single change. Note all changes that contribute to the tier.
7. Record the rationale, citing the changed paths and values that drove the tier.

## Base Tiers By Change Type

These criteria are review-priority criteria, not mechanical reproductions of TrialDiff classifier thresholds. Where magnitude matters, apply it as principled judgment rather than as a hard classifier-derived cutoff.

### Critical

Use `critical` when the change could materially alter interpretation of the trial's primary evidence, indicates a possible high-priority conduct or safety concern, or removes important interpretability information at a late stage.

Examples:

- Primary outcome measure added, removed, or substantively redefined, including a change to what is measured or the primary timepoint.
- Primary analysis population or primary endpoint definition changed when data collection would plausibly be underway or complete.
- Trial moved to terminated, withdrawn, or suspended status with `whyStopped` absent, null, empty, placeholder-only, or otherwise effectively non-explanatory.
- Enrollment reduced to zero.
- Primary outcome, secondary outcome, or reported result removed after the trial reached completed or terminal status.
- Serious adverse event results removed without clear source context.

### High

Use `high` when the change is consequential for trial design, interpretation, conduct, or review priority, but is less determinative, less unusually timed, or better explained than a critical change.

Examples:

- Secondary outcome added, removed, or substantively redefined before completion.
- Eligibility criteria changed in a way that plausibly shifts the study population after recruitment has begun.
- Intervention, dose, schedule, comparator, or arm structure changed.
- Substantial enrollment reduction that plausibly reflects recruitment failure or truncation, short of zeroing.
- Trial moved to terminal status with a present but low-specificity operational or business explanation.
- Large slip in primary completion or study completion date at a late stage, on the order of a year or more as a review-priority judgment.
- Serious adverse event results added or substantively modified.

### Medium

Use `medium` when the change is substantive and worth recording, but appears routine, expected, lower consequence, or not unusually timed.

Examples:

- Moderate timeline movement outside a late-stage or post-completion context.
- Minor eligibility refinement that does not clearly shift the study population.
- Enrollment change too small to plausibly affect interpretation of feasibility or power.
- Outcome wording refinement that does not change what is measured.
- Non-primary design text clarification that does not change arms, intervention, population, or endpoint interpretation.

### Low

Use `low` when the change is real but unlikely to affect interpretation.

Examples:

- Small timeline adjustment.
- Routine status progression, such as recruiting to active/not recruiting.
- Peripheral metadata update with limited interpretive value.
- Results-reconciliation-only outcome text change after `/hasResults` or `/resultsSection` appears, where no independent substantive change is visible.

### Administrative / Uncategorized

Use `administrative/uncategorized` when the change has no independent review value.

Examples:

- Contact churn.
- Location churn.
- Sponsor administrative metadata.
- Formatting-only or non-substantive text updates.
- Registry housekeeping fields with no substantive interpretive effect.

## Timing Escalation

Timing can increase review priority when a sensitive field changes late in the trial lifecycle.

Sensitive fields include:

- outcome definitions;
- endpoint timing;
- eligibility criteria;
- analysis population;
- primary completion or study completion dates;
- intervention or arm structure.

Escalation guidance:

- A sensitive substantive change during active/not-recruiting or late recruitment may escalate one tier.
- A sensitive substantive change after completion or after a terminal status may escalate to critical.
- Timing does not escalate purely administrative changes.
- Timing does not escalate results-reconciliation-only changes unless there is a substantive independent change apart from the results posting.

## Insufficient Evidence

Do not over-assign severity when the record does not support it.

Use `insufficient evidence` or record an ambiguity note when:

- source provenance is missing or unverifiable;
- the old value cannot be reconstructed where old/new comparison is essential;
- an outcome change cannot be distinguished from results reconciliation;
- the changed paths are too broad to determine what substantive change occurred;
- the patch payload does not support the apparent category.

Absence or thinness of `whyStopped` may be high or critical review priority. It is never, by itself, a finding of misconduct, sponsor intent, or regulatory non-compliance.

## Boundaries

This rubric assigns review priority to a registry change as represented in ClinicalTrials.gov. The reviewer must not assign:

- misconduct, fraud, or wrongdoing;
- sponsor intent or motivation;
- manuscript-disclosure status;
- regulatory compliance or non-compliance;
- clinical significance of the underlying medical question;
- whether the amendment was scientifically justified.

## Stage 2 Comparison

After the stage 1 reviewer tier and rationale are recorded, reveal TrialDiff's assigned severity, category, rules fired, value signals, and timing-context label.

Stage 2 compares the independent tier to TrialDiff's tier and records:

- agreement;
- false-positive critical/high classifications;
- false-negative material records;
- ambiguous cases;
- categories that over-fire;
- categories that under-fire;
- source/provenance failures;
- recommended rule changes.

## Use In Calibration

- This rubric is frozen by committing it to the repository.
- The rubric commit hash is the rubric identity.
- The calibration sample (`CALIBRATION_SAMPLE_PLAN_v0.2.md`) is drawn and reviewed only after this file is committed.
- `SEVERITY_CALIBRATION_v0.2.md` must cite this rubric's commit hash.
- `SEVERITY_CALIBRATION_v0.2.md` must state which independence path was used.
