# Calibration Sample Plan - TrialDiff v0.2

Status: DRAFT - freeze by committing before any sample is drawn or reviewed.
Date: 2026-06-18
Depends on: `V0.2_SCOPE.md`; `SEVERITY_RUBRIC_v0.2.md` frozen at commit `a764e33`

## 1. Purpose

This plan defines, before any record is reviewed, how the TrialDiff v0.2 calibration sample is drawn, what the reviewer sees, who reviews it, and how agreement or disagreement is scored.

The goal is to prevent the calibration result from being shaped after the fact.

## 2. Corpus Source And Sequencing

Calibration begins on the existing 25-study alpha corpus, not on a future expanded corpus.

Rationale: the v0.2 stop-condition thresholds gate the `critical` and `critical`/`high` review-priority bands. The alpha corpus already contains enough critical and high records to test those gates:

- 35 critical;
- 51 high.

Validating the rule set here, before corpus expansion, reduces the risk of scaling a classifier that later proves to over-fire.

Medium and low tiers are included for boundary information but are not the primary pass/fail gate. The 25-study corpus contains:

- 11 medium;
- 25 low;
- 0 separately labeled administrative events in `materiality_events`.

The medium tier is therefore sampled exhaustively in this slice. A broader medium/low completeness pass remains deferred to the expanded corpus.

## 3. Source Table And Stratification

Sample from `materiality_events`, not only from `evidence_records`, because medium and low rows are not first-class Evidence Records in v0.1-alpha.

Resolved alpha-corpus strata:

| Tier | Available | Sample N | Status |
|---|---:|---:|---|
| critical | 35 | 30 | threshold-gated |
| high | 51 | 30 | threshold-gated |
| medium | 11 | 11 | exhaustive, below target |
| low | 25 | 20 | boundary sample |

Total sample size: 91 records.

Within each tier, preserve the change-family mix where possible. At minimum, report the family composition of the realized sample across:

- outcome;
- timeline;
- enrollment/status;
- design/intervention;
- eligibility;
- adverse events, if present;
- administrative or metadata-like changes.

Do not over-sample a rare family to the point of distorting the tier. If a family is absent from a tier, record that absence rather than forcing representation.

## 4. Sampling Method

Sampling must be reproducible from the committed plan and seed.

Seed:

```text
trialdiff-v0.2-calibration-a764e33
```

Stable sample key:

```text
nct_id|from_version|to_version|category|severity|changed_paths_json|raw_hash
```

Sampling procedure:

1. Build the candidate set from `materiality_events`.
2. For each row, compute `sha256(seed + "|" + stable_sample_key)`.
3. Sort ascending by that hash within each severity tier.
4. Take the target count for each tier.
5. Record the selected rows in the calibration report.

For high and critical rows that also have an Evidence Record, include the public `event_id` from `evidence_records`. For medium and low rows, use the stable sample key plus the internal materiality event `id`.

The calibration report must include:

- seed;
- sample query or script;
- selected `materiality_events.id` values;
- public Evidence Record IDs where available;
- realized severity counts;
- realized category/family counts.

## 5. Stage 1 Reviewer Inputs

For each sampled record, the reviewer receives only raw or source-derived material:

- changed JSON Pointer paths;
- patch operations and new values;
- reconstructed old values from the FROM-version snapshot where old/new comparison is needed;
- raw FROM-version status fields, including overall status and relevant date fields;
- source URLs;
- hashes;
- version numbers.

The reviewer does not see:

- TrialDiff's assigned severity;
- TrialDiff's category label;
- TrialDiff's deterministic rules fired;
- TrialDiff's value signals;
- TrialDiff's derived timing-context label;
- any TrialDiff-generated explanatory summary.

The reviewer derives timing context from the raw FROM-version status fields.

## 6. Reviewer

Default reviewer mechanism: fresh-context model review against the frozen rubric.

The reviewer must be a model instance with no exposure to:

- TrialDiff classifier internals;
- the v0.2 planning conversation;
- existing TrialDiff severity labels for the sample;
- rules fired for the sample;
- category labels for the sample.

This is labeled as:

```text
adversarial-model review against a frozen rubric
```

It is not external clinical validation.

If a domain expert later reviews the sample instead of, or in addition to, the fresh-context model, the calibration report may label that portion as external domain review.

## 7. Two-Stage Procedure

Stage 1: blind assignment.

The reviewer applies `SEVERITY_RUBRIC_v0.2.md` at commit `a764e33` using only the inputs listed in Section 5. For each row, the reviewer records:

- assigned tier;
- one-line characterization of the change;
- one-line rationale;
- driving changed paths;
- ambiguity or insufficient-evidence flag, if applicable.

Stage 2: reveal and diagnose.

Only after the stage 1 judgment is recorded, reveal:

- TrialDiff severity;
- TrialDiff category;
- rules fired;
- value signals;
- derived timing-context label.

Then record:

- agreement or disagreement;
- disagreement direction;
- likely reason for disagreement;
- whether a rule category appears to over-fire or under-fire.

## 8. Scoring

Reference standard: the independent rubric-based tier is the constructed reference for this calibration. It is not ground truth.

Per record, record:

- materiality event `id`;
- stable sample key;
- Evidence Record `event_id`, if available;
- reviewer tier;
- TrialDiff tier;
- agreement;
- disagreement direction;
- ambiguity flag;
- insufficient-evidence flag.

False-positive definitions:

- False-positive critical: TrialDiff is `critical`, reviewer is below `critical`.
- False-positive high-priority: TrialDiff is `critical` or `high`, reviewer is below `high`.

False-negative definition:

- False negative: reviewer tier is higher than TrialDiff tier.

Ambiguous or insufficient-evidence cases are reported separately and excluded from rate denominators, with counts disclosed. They may not be used to deflate a false-positive rate.

Outputs for `SEVERITY_CALIBRATION_v0.2.md`:

- confusion table: reviewer tier by TrialDiff tier;
- false-positive rate among TrialDiff `critical`;
- false-positive rate among TrialDiff `critical`/`high` high-priority records;
- false-negative summary;
- per-family over-fire or under-fire summary;
- ambiguous and insufficient-evidence counts;
- recommended rule changes, if any.

## 9. Pass / Fail

The brief proceeds only if all of the following hold:

- false-positive rate among TrialDiff `critical` records is below 20%;
- false-positive rate among TrialDiff `critical`/`high` high-priority records is below 25%;
- no whole rule family is systematically mis-tiered;
- no unresolved source/provenance failure affects a flagship candidate;
- no manuscript-disclosure or misconduct claim is made without independent document review.

If any condition fails:

- pause for rule revision;
- assign a new `rule_set_hash`;
- regenerate Evidence Records;
- rerun calibration against the revised rule set before producing a buyer-facing brief.

v0.1-alpha remains frozen regardless.

## 10. Freeze

Commit this plan before drawing the sample.

`SEVERITY_CALIBRATION_v0.2.md` must cite:

- the rubric commit hash: `a764e33`;
- this sample-plan commit hash;
- the sampling seed;
- the selected sample list;
- the reviewer mechanism used.
