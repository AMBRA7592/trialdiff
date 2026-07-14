# Manual Audit: 5 Alpha Evidence Records

> **Erratum (2026-07-14, see `ERRATA.md` E3):** the line "Severity means
> review priority" below reflects the pre-calibration framing under which
> this audit was written. The v0.2/v0.2.1 calibration subsequently failed
> its gate and severity was decoupled from review priority
> (`SEVERITY_DECOUPLING_v0.2.1.md`). Read severity here as deterministic,
> uncalibrated triage metadata. The audit's structural findings are
> unaffected.

Audit date: 2026-06-17

Audit scope: five selected records from `records/`, chosen to cover post-recruitment outcome changes, status termination, timeline movement, secondary outcome change, and enrollment change.

This is a structural audit: it checks record integrity, source/provenance fields, rule attribution, and claim boundaries. It is not a severity-calibration audit. It does not judge scientific justification, sponsor intent, manuscript disclosure, misconduct, or regulatory compliance.

> Severity means review priority, not proven wrongdoing.

## 1. evt_NCT04754399_v5_v6_b771bc8b911e

- Trial: NCT04754399
- Title: Cannabidiol (CBD) for Treatment of Aromatase Inhibitor-Associated Arthralgias
- Sponsor: University of Michigan Rogel Cancer Center
- Versions: 5 to 6
- Submitted date: 2024-09-26
- Category: primary_outcome_change
- Severity: critical
- Timing context: post_recruitment
- Rules: primary_outcome_any_change; secondary_outcome_any_change
- Changed paths: 15
- Patch hash prefix: 40f1b909b8bfa7a2
- Canonical hash prefix: 2bad3daa3ae2201a

Important confound: this patch is not a clean standalone outcome-change example. The changed paths include `/hasResults` and `/resultsSection`, meaning the outcome-field changes are co-incident with results becoming present in the registry record. A plausible interpretation is results-posting or results-reconciliation cleanup rather than prospective outcome switching.

Audit result: record contains study metadata, changed outcome paths, version references, rule attribution, provenance hashes, supported claims, and explicit non-claims. The record is valid as a review-priority Evidence Record, but it should not be used as a flagship example of outcome switching or undisclosed outcome change without separate document review.

## 2. evt_NCT05180006_v3_v4_3cebafd518aa

- Trial: NCT05180006
- Title: Impact of Neoadjuvant Immunotherapy in Early Stage Breast Cancer Before Standard Therapy
- Sponsor: Gustave Roussy, Cancer Campus, Grand Paris
- Versions: 3 to 4
- Submitted date: 2025-11-24
- Category: status_termination
- Severity: critical
- Timing context: early_recruitment
- Rules: contact_admin_change; enrollment_count_change; enrollment_type_change; terminal_status_change; why_stopped_change
- Changed paths: 14
- Patch hash prefix: 3282eb736dafd492
- Canonical hash prefix: 71f44572273471d5

Audit result: record contains status/termination-related rule attribution, source/provenance fields, and the explicit non-claim that TrialDiff does not determine regulatory compliance or non-compliance.

## 3. evt_NCT02942355_v26_v27_f30d5b213a35

- Trial: NCT02942355
- Title: Trial of Anastrozole and Palbociclib in Metastatic HER2-Negative Breast Cancer
- Sponsor: Wake Forest University Health Sciences
- Versions: 26 to 27
- Submitted date: 2026-05-04
- Category: timeline_major_slip
- Severity: critical
- Timing context: late_recruitment
- Rules: none; classified through timeline value signal logic
- Changed paths: 5
- Patch hash prefix: a276afa02678cbef
- Canonical hash prefix: 19e739305e3af118

Audit result: record contains timeline date paths, value-signal classification, provenance hashes, and the explicit boundary that TrialDiff does not infer clinical significance or sponsor intent.

## 4. evt_NCT01441947_v16_v17_1493ccf4a7cd

- Trial: NCT01441947
- Title: Cabozantinib in Women With Metastatic Hormone-Receptor-Positive Breast Cancer
- Sponsor: Massachusetts General Hospital
- Versions: 16 to 17
- Submitted date: 2023-01-07
- Category: secondary_outcome_change
- Severity: critical
- Timing context: late_recruitment
- Rules: secondary_outcome_any_change
- Changed paths: 5
- Patch hash prefix: 24334e62db3c941a
- Canonical hash prefix: 27488b4aae8a05f0

Audit result: record contains secondary-outcome path evidence and the category-specific non-claim that TrialDiff does not determine whether the registry outcome change reflects outcome switching rather than a legitimate registry correction.

## 5. evt_NCT03197935_v19_v20_0ab34beeb3be

- Trial: NCT03197935
- Title: A Study to Investigate Atezolizumab and Chemotherapy Compared With Placebo and Chemotherapy in the Neoadjuvant Setting in Participants With Early Stage Triple Negative Breast Cancer
- Sponsor: Hoffmann-La Roche
- Versions: 19 to 20
- Submitted date: 2019-04-26
- Category: enrollment_change
- Severity: critical
- Timing context: late_recruitment
- Rules: contact_admin_change; enrollment_count_change; enrollment_type_change
- Changed paths: 501
- Patch hash prefix: aa0c338cdd08801a
- Canonical hash prefix: 5d2c4de903ada1d4

Audit result: record contains enrollment-related rule attribution, large-patch provenance, changed-path evidence, and explicit non-claims limiting interpretation.

## Conclusion

All five audited records answer the 30-day inspection questions:

- what changed;
- where it changed;
- when it changed;
- which rule or signal classified it;
- why it is review-priority;
- what source/provenance/hash fields support it;
- what is explicitly not claimed.
