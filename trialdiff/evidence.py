from __future__ import annotations

from dataclasses import dataclass
import json
from sqlite3 import Row
from typing import Any

from trialdiff.constants import Source
from trialdiff.provenance import canonical_json, sha256_json, sha256_text, utc_now_iso


EVIDENCE_VERSION = 1
CLINICALTRIALS_STUDY_URL = "https://clinicaltrials.gov/study/{nct_id}"

STANDARD_CLAIMS_NOT_SUPPORTED = [
    "That the amendment was scientifically unjustified.",
    "That the change constitutes misconduct or wrongdoing.",
    "That sponsor intent can be inferred from this registry change.",
    "That the change caused or altered the trial's results.",
    "That the change was or was not disclosed in a manuscript.",
    "That TrialDiff determines regulatory compliance or non-compliance.",
]

CATEGORY_CLAIM_TEMPLATES: dict[str, list[str]] = {
    "primary_outcome_change": [
        "A registry field under the primary outcome module changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "secondary_outcome_change": [
        "A registry field under the secondary outcome module changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "design_change": [
        "A registry field under the study design module changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "arm_intervention_change": [
        "A registry field under an arm or intervention module changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "eligibility_change": [
        "A registry field under the eligibility module changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "status_termination": [
        "A registry field under the status or stopped-trial explanation module changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "enrollment_change": [
        "A registry field under enrollment changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "timeline_major_slip": [
        "A trial timeline date field moved by more than 365 days between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "timeline_significant_shift": [
        "A trial timeline date field moved by more than 90 days between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "serious_adverse_event_addition": [
        "A registry path under serious adverse event results was added between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "serious_adverse_event_modification": [
        "A registry path under serious adverse event results changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "serious_adverse_event_removal": [
        "A registry path under serious adverse event results was removed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "other_adverse_event_addition": [
        "A registry path under non-serious adverse event results was added between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "other_adverse_event_modification": [
        "A registry path under non-serious adverse event results changed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
    "other_adverse_event_removal": [
        "A registry path under non-serious adverse event results was removed between ClinicalTrials.gov versions {from_version} and {to_version}.",
    ],
}

CATEGORY_CLAIMS_NOT_SUPPORTED: dict[str, list[str]] = {
    "status_termination": [
        "That TrialDiff determines whether the stopped-trial explanation satisfies 42 CFR 11.64.",
    ],
    "primary_outcome_change": [
        "That the outcome change was inconsistent with the protocol or statistical analysis plan.",
    ],
    "secondary_outcome_change": [
        "That this registry outcome change reflects outcome switching rather than a legitimate registry correction.",
        "That the outcome change was inconsistent with the protocol or statistical analysis plan.",
    ],
    "serious_adverse_event_removal": [
        "That the removed adverse event record was scientifically or legally improper.",
    ],
}

REVIEW_QUESTIONS: dict[str, str] = {
    "primary_outcome_change": (
        "What did the primary outcome field say before and after the amendment, and is there a public "
        "protocol, statistical analysis plan, or manuscript explaining the change?"
    ),
    "secondary_outcome_change": (
        "What did the secondary outcome field say before and after the amendment, and what contemporaneous "
        "public document explains the change?"
    ),
    "status_termination": (
        "Does the public registry record give a specific explanation for the stopped or terminal status?"
    ),
    "enrollment_change": (
        "What explains the enrollment change, and does the change affect interpretation of trial feasibility or power?"
    ),
    "timeline_major_slip": (
        "What explains the major timeline movement, and does the amendment represent a delay, a backfill, or a correction?"
    ),
    "timeline_significant_shift": (
        "What explains the timeline movement, and is it consistent with the trial's recruitment and reporting history?"
    ),
    "serious_adverse_event_removal": (
        "What source document explains the change to the serious adverse event results record?"
    ),
    "serious_adverse_event_addition": (
        "What source document explains the added serious adverse event results record?"
    ),
    "serious_adverse_event_modification": (
        "What source document explains the modified serious adverse event results record?"
    ),
}


@dataclass(frozen=True)
class EvidenceGenerationResult:
    generated: int
    skipped: int
    deleted: int


def build_event_id(
    *,
    nct_id: str,
    from_version: int,
    to_version: int,
    patch_hash: str,
    category: str,
    changed_paths: list[str],
    rule_set_hash: str,
    evidence_version: int,
    event_classes: list[str] | None = None,
) -> str:
    digest = sha256_json(
        {
            "nct_id": nct_id,
            "from_version": from_version,
            "to_version": to_version,
            "patch_hash": patch_hash,
            "category": category,
            "changed_paths": sorted(changed_paths),
            "event_classes": sorted(event_classes or []),
            "rule_set_hash": rule_set_hash,
            "evidence_version": evidence_version,
        }
    )[:12]
    return f"evt_{nct_id}_v{from_version}_v{to_version}_{digest}"


def generate_evidence_records(
    store: Any,
    *,
    nct_id: str | None = None,
    force: bool = False,
    evidence_version: int = EVIDENCE_VERSION,
) -> EvidenceGenerationResult:
    deleted = store.delete_evidence_records(nct_id) if force else 0
    generated = 0
    skipped = 0
    for row in store.iter_evidence_source_rows(nct_id):
        if store.evidence_record_exists(
            nct_id=row["nct_id"],
            from_version=row["from_version"],
            to_version=row["to_version"],
            rule_set_hash=row["rule_set_hash"],
            evidence_version=evidence_version,
        ):
            skipped += 1
            continue
        record = build_evidence_record(row, evidence_version=evidence_version)
        inserted = store.insert_evidence_record(record)
        generated += inserted
        skipped += 0 if inserted else 1
    return EvidenceGenerationResult(generated=generated, skipped=skipped, deleted=deleted)


def build_evidence_record(row: Row | dict[str, Any], *, evidence_version: int = EVIDENCE_VERSION) -> dict[str, Any]:
    data = dict(row)
    categories = load_json(data["categories_json"], [])
    changed_paths = load_json(data["changed_paths_json"], [])
    deterministic_rules = load_json(data["deterministic_rules_json"], [])
    value_signals = load_json(data["value_signals_json"], [])
    event_classes = load_json(data.get("event_classes_json"), [])
    patch = load_json(data["patch_json"], [])
    generated_at = utc_now_iso()
    event_id = build_event_id(
        nct_id=data["nct_id"],
        from_version=data["from_version"],
        to_version=data["to_version"],
        patch_hash=data["patch_hash"],
        category=data["category"],
        changed_paths=changed_paths,
        event_classes=event_classes,
        rule_set_hash=data["rule_set_hash"],
        evidence_version=evidence_version,
    )
    claims_supported = build_claims_supported(
        data=data,
        changed_paths=changed_paths,
        event_classes=event_classes,
        deterministic_rules=deterministic_rules,
        value_signals=value_signals,
    )
    claims_not_supported = build_claims_not_supported(data["category"], event_classes=event_classes)
    review_question = review_question_for_category(data["category"])
    citation_text = citation_for_record(
        event_id=event_id,
        nct_id=data["nct_id"],
        from_version=data["from_version"],
        to_version=data["to_version"],
        evidence_version=evidence_version,
    )
    canonical = {
        "schema": "trialdiff.evidence_record",
        "evidence_version": evidence_version,
        "event_id": event_id,
        "trial": {
            "nct_id": data["nct_id"],
            "clinicaltrials_gov_url": CLINICALTRIALS_STUDY_URL.format(nct_id=data["nct_id"]),
        },
        "versions": {
            "from_version": data["from_version"],
            "to_version": data["to_version"],
            "submitted_date": data.get("submitted_date"),
        },
        "classification": {
            "severity_pre_timing": data["severity_pre_timing"],
            "severity": data["severity"],
            "triage_label": data["severity"],
            "calibration_status": "uncalibrated",
            "category": data["category"],
            "categories": categories,
            "event_classes": event_classes,
            "timing_context": data.get("timing_context"),
            "deterministic_rules": deterministic_rules,
            "value_signals": value_signals,
            "triage_rule_set_hash": data.get("triage_rule_set_hash", data["rule_set_hash"]),
            "event_class_rule_set_hash": data.get("event_class_rule_set_hash"),
            "rule_set_hash": data["rule_set_hash"],
        },
        "changed_paths": changed_paths,
        "patch": patch,
        "provenance": {
            "patch_hash": data["patch_hash"],
            "patch_source": data["patch_source"],
            "patch_source_url": data.get("patch_source_url") or "",
            "patch_raw_hash": data.get("patch_raw_hash") or "",
            "from_snapshot_hash": data.get("from_snapshot_hash"),
            "to_snapshot_hash": data.get("to_snapshot_hash"),
            "materiality_event_hash": data.get("materiality_event_hash") or "",
        },
        "claims_supported": claims_supported,
        "claims_not_supported": claims_not_supported,
        "review_question": review_question,
        "citation_text": citation_text,
    }
    canonical_text = canonical_json(canonical)
    return {
        "event_id": event_id,
        "nct_id": data["nct_id"],
        "from_version": data["from_version"],
        "to_version": data["to_version"],
        "submitted_date": data.get("submitted_date"),
        "timing_context": data.get("timing_context"),
        "severity_pre_timing": data["severity_pre_timing"],
        "severity": data["severity"],
        "category": data["category"],
        "categories": categories,
        "event_classes": event_classes,
        "changed_paths": changed_paths,
        "deterministic_rules": deterministic_rules,
        "value_signals": value_signals,
        "claims_supported": claims_supported,
        "claims_not_supported": claims_not_supported,
        "review_question": review_question,
        "citation_text": citation_text,
        "canonical": canonical,
        "canonical_hash": sha256_text(canonical_text),
        "evidence_version": evidence_version,
        "patch_hash": data["patch_hash"],
        "patch_source": data["patch_source"],
        "patch_source_url": data.get("patch_source_url") or "",
        "patch_raw_hash": data.get("patch_raw_hash") or "",
        "from_snapshot_hash": data.get("from_snapshot_hash"),
        "to_snapshot_hash": data.get("to_snapshot_hash"),
        "materiality_event_hash": data.get("materiality_event_hash") or "",
        "rule_set_hash": data["rule_set_hash"],
        "source": Source.DERIVED_EVIDENCE_RECORD.value,
        "source_url": f"trialdiff://evidence-record/{event_id}",
        "generated_at": generated_at,
    }


def build_claims_supported(
    *,
    data: dict[str, Any],
    changed_paths: list[str],
    event_classes: list[str],
    deterministic_rules: list[str],
    value_signals: list[dict[str, Any]],
) -> list[str]:
    claims = [
        (
            "TrialDiff compared ClinicalTrials.gov record version {from_version} to version {to_version} "
            "for {nct_id}."
        ).format(**data),
        "The JSON Patch for this comparison has hash {patch_hash}.".format(**data),
        "The active deterministic rule set hash was {rule_set_hash}.".format(**data),
        (
            "The deterministic triage label was {severity}; before timing adjustment it was {severity_pre_timing}."
        ).format(**data),
        "The triage label is uncalibrated metadata, not a validated review-priority finding.",
    ]
    if event_classes:
        claims.append(
            "The patch satisfied these deterministic event-class predicates: {classes}.".format(
                classes=", ".join(event_classes)
            )
        )
    claims.extend(template.format(**data) for template in CATEGORY_CLAIM_TEMPLATES.get(data["category"], []))
    if data.get("timing_context"):
        claims.append(
            "The timing context for the from-version record was {timing_context}.".format(**data)
        )
    if deterministic_rules:
        claims.append("The deterministic rules that fired were: {rules}.".format(rules=", ".join(deterministic_rules)))
    if changed_paths:
        claims.append("The changed JSON Pointer paths were: {paths}.".format(paths=", ".join(changed_paths)))
    claims.extend(signal_claims(value_signals))
    claims.extend(event_class_claims(event_classes, data))
    if any(path.endswith("/whyStopped") or "/whyStopped" in path for path in changed_paths):
        claims.append(
            "The changed paths include the ClinicalTrials.gov whyStopped field, a stopped-trial explanation field relevant to 42 CFR 11.64 when applicable."
        )
    return unique(claims)


def build_claims_not_supported(category: str, *, event_classes: list[str]) -> list[str]:
    claims = STANDARD_CLAIMS_NOT_SUPPORTED + CATEGORY_CLAIMS_NOT_SUPPORTED.get(category, [])
    if "outcome_edit_cooccurs_with_results_posting" in event_classes:
        claims.append(
            "That co-occurrence with results posting proves the outcome edit was harmless, administrative, or substantively benign."
        )
    if event_classes:
        claims.append("That event-class membership is a validated global review-priority ranking.")
    return unique(claims)


def event_class_claims(event_classes: list[str], data: dict[str, Any]) -> list[str]:
    claims: list[str] = []
    from_version = data["from_version"]
    to_version = data["to_version"]
    for event_class in event_classes:
        if event_class == "primary_endpoint_changed_after_primary_completion_without_results_reconciliation":
            claims.append(
                f"A primary outcome definition field changed after primary completion between versions {from_version} and {to_version}, without a results-posting co-occurrence signal."
            )
        elif event_class == "secondary_outcome_removed_after_primary_completion":
            claims.append(
                f"The JSON Patch removed a whole secondary outcome item after primary completion between versions {from_version} and {to_version}; when a TO-version outcome list is available, reindex-only removals are excluded."
            )
        elif event_class == "enrollment_changed_to_zero":
            claims.append(f"The enrollment count changed from a positive value to zero between versions {from_version} and {to_version}.")
        elif event_class == "why_stopped_removed_in_terminal_context":
            claims.append(
                f"The whyStopped field changed from nonempty to empty or absent in a terminal-status context between versions {from_version} and {to_version}."
            )
        elif event_class == "outcome_edit_cooccurs_with_results_posting":
            claims.append(
                f"An outcome path changed between versions {from_version} and {to_version} in a patch that also carried a hasResults or resultsSection co-occurrence signal."
            )
    return claims


def signal_claims(value_signals: list[dict[str, Any]]) -> list[str]:
    claims: list[str] = []
    for signal in value_signals:
        signal_name = signal.get("signal")
        if signal_name == "why_stopped_empty":
            claims.append("The whyStopped value was empty or removed in the changed registry record.")
        elif signal_name == "why_stopped_low_information":
            claims.append("The whyStopped value matched TrialDiff's low-information phrase list.")
        elif signal_name == "enrollment_zeroed":
            claims.append("The enrollment count changed from a positive value to zero.")
        elif signal_name == "enrollment_count_change_ge_20pct":
            claims.append("The enrollment count changed by at least 20 percent.")
        elif isinstance(signal_name, str) and signal_name.startswith("timeline_"):
            delta_days = signal.get("delta_days")
            if delta_days is not None:
                claims.append(f"The timeline value moved by {delta_days} days.")
            else:
                claims.append("A timeline value changed and was classified by TrialDiff's timeline signal rules.")
    return claims


def review_question_for_category(category: str) -> str:
    return REVIEW_QUESTIONS.get(
        category,
        "What source document explains this registry amendment, and does it change interpretation of the trial record?",
    )


def citation_for_record(
    *,
    event_id: str,
    nct_id: str,
    from_version: int,
    to_version: int,
    evidence_version: int,
) -> str:
    return (
        f"TrialDiff Evidence Record {event_id}. ClinicalTrials.gov {nct_id}, "
        f"versions {from_version}-{to_version}. Evidence version {evidence_version}."
    )


def load_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result
