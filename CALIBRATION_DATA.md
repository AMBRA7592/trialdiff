# Calibration Data — Index, Blinding Status, and Redaction Record

This file indexes the v0.2/v0.2.1 severity-calibration data files, states
their blinding status, and records the personal-data redaction applied on
2026-07-14. Integrity anchor: `MANIFEST.calibration.sha256`.

> **Contamination notice for future reviewers.** If you may ever serve as a
> blinded reviewer in a future TrialDiff calibration round, do not read the
> unblinding keys or the adjudication packages below. The blinded review
> design depends on reviewers having no exposure to TrialDiff's own labels.

## Files

| File | Round | Role |
| --- | --- | --- |
| `CALIBRATION_SAMPLE_PLAN_v0.2.md` | v0.2 | Pre-registered sample + blinding design |
| `CALIBRATION_SAMPLE_v0.2.csv` / `_v0.2.1.csv` | both | Drawn samples (blinded ids) |
| `CALIBRATION_REVIEW_PACKAGE_v0.2.jsonl` / `_v0.2.1.jsonl` | both | Blinded review inputs (what reviewers saw) |
| `CALIBRATION_REVIEWER_1/2_v0.2.jsonl`, `_v0.2.1.jsonl` | both | Filed reviewer outputs |
| `CALIBRATION_REVIEW_ADJUDICATION_PACKAGE_v0.2.1.jsonl` | v0.2.1 | Adjudication inputs |
| `CALIBRATION_REVIEW_CRITICAL_STRATUM_ADJUDICATION_PACKAGE_v0.2.1.jsonl` | v0.2.1 | Full critical-stratum adjudication inputs |
| `CALIBRATION_REVIEW_CROSSWALK_UNBLINDING_KEY_v0.2.csv` / `_v0.2.1.csv` | both | **Unblinding keys** (blinded id → TrialDiff labels) |

Reviewer-apparatus provenance is documented in `CALIBRATION_REVIEWERS.md`.

## Blinding status (honest accounting)

Both calibration rounds are **closed**; their unblinding keys are published
deliberately, as the post-close reveal that makes the scoring auditable.

Acknowledged limitation: during the v0.2 and v0.2.1 rounds the keys were
committed to the repository as the rounds ran, rather than sealed until
close. The reviewers were fresh model contexts initialized without
repository access, so the practical contamination risk was low, but the
protocol was not airtight. Future rounds must use the commit–reveal
procedure in `RELEASING.md` §E: commit only the key's SHA-256 while review
is open; publish the key after adjudication closes.

## Personal-data redaction (2026-07-14)

The four review/adjudication packages embed full ClinicalTrials.gov records
and patch payloads, which carried site-contact and study-contact personal
data (names, emails, phone numbers — roughly 9,000 email instances,
including personal-domain addresses and mobile numbers of named site
staff). These values have no analytical role: classification rules match
JSON Pointer paths, never contact values, and reviewer scoring never keyed
on them. They were redacted in place with
`scripts/redact_calibration_contacts.py` (deterministic and idempotent:
structured `email`/`phone`/`phoneExt` fields, `name` fields in
person-contexts, pointer-addressed contact scalars in patch operations and
value contexts, and email addresses inside free text). JSON Pointer paths
and all review-relevant fields are byte-unchanged.

| File | SHA-256 before | SHA-256 after |
| --- | --- | --- |
| `CALIBRATION_REVIEW_PACKAGE_v0.2.jsonl` | `9582fa2c41aceba7ace8ffb747531694f56486127d39b16cd8d83d061c323662` | `25de9d16acdd5ece3640595a89939d699f6372986042c95a01cee43d78c41ba6` |
| `CALIBRATION_REVIEW_PACKAGE_v0.2.1.jsonl` | `bd337cc6319121e1081ab4aa5594829a52e69c386f60689194862a4856e768e9` | `5c482d47ec0b7483c294c69c2ae28d9cbfb110a489c61c83d8695bfe35a8a423` |
| `CALIBRATION_REVIEW_ADJUDICATION_PACKAGE_v0.2.1.jsonl` | `331908f0b29ed4dc758d5dbe2a61b2f5f67439780182f338fd0c0c6a96011b29` | `2f3e95d5ce76e02ee4654d572fc7f1187242750a25f2ae19fbbe394722037f85` |
| `CALIBRATION_REVIEW_CRITICAL_STRATUM_ADJUDICATION_PACKAGE_v0.2.1.jsonl` | `197baae4125bfc697196ae05dfe9280f16e59f71f7d2f5d059f7b2f07d9a1fa8` | `c5a043032ace40b8e0c626423c20215fe3897a0e76f69cc3b264035925d3e34c` |

Methodological note: the redaction post-dates the reviews, so the packages
are no longer byte-identical to what reviewers saw; the before-hashes above
and git history preserve the exact originals for audit. Because git history
(and the `trialdiff-public` snapshot) retains the pre-redaction bytes, the
redaction removes the data from the browsable tip, not from history — a
deliberate trade against breaking the audit trail.

The frozen evidence-record packages (`records/`,
`event_class_records_v0.1.1/`) also contain small amounts of verbatim
registry contact data (a few dozen email instances inside cited patches).
Those files are hash-pinned citations of public registry content and are
not modified; see `DATA_LICENSE.md` for the registry-provenance note.

Reviewer outputs, samples, and crosswalks contained no personal contact
data (verified by scan) and are unmodified.
