from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from sqlite3 import Row
from typing import Any

from trialdiff.classifier.pathmatch import match_path
from trialdiff.classifier.timing import LATE_RECRUITMENT, POST_RECRUITMENT, UNKNOWN, timing_context_from_record
from trialdiff.constants import Source
from trialdiff.jsonpatch import MISSING, PatchValueContext, apply_patch as apply_json_patch, build_value_contexts, resolve_pointer
from trialdiff.provenance import Provenance, sha256_json, utc_now_iso


SEVERITY_RANK = {"ignore": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
RANK_SEVERITY = {rank: severity for severity, rank in SEVERITY_RANK.items()}
TIMING_SENSITIVE_CATEGORIES: set[str] = set()
OUTCOME_CHANGE_CATEGORIES = {"primary_outcome_change", "secondary_outcome_change"}
TIMELINE_RULE_CATEGORY = "timeline_shift"
TIMELINE_DATE_STRUCTS = {
    "/protocolSection/statusModule/startDateStruct",
    "/protocolSection/statusModule/primaryCompletionDateStruct",
    "/protocolSection/statusModule/completionDateStruct",
}
ANTICIPATED_DATE_TYPES = {"ANTICIPATED", "ESTIMATED"}
ACTUAL_DATE_TYPES = {"ACTUAL"}
LOW_INFORMATION_STOP_PHRASES = {
    "administrative",
    "business decision",
    "no longer applicable",
    "not moving forward",
    "partner",
    "acquired",
    "abandon",
    "pi departure",
    "pi left",
    "principal investigator left",
    "investigator left",
    "administrative reasons",
    "feasibility",
    "site closure",
    "sponsor decision",
    "strategic decision",
    "terminated by sponsor",
    "withdrawn by sponsor",
}


@dataclass(frozen=True)
class ClassifierRule:
    rule_key: str
    path_pattern: str
    op_filter: list[str]
    value_filter: dict[str, Any]
    severity: str
    category: str
    timing_sensitive: bool
    description: str

    @classmethod
    def from_row(cls, row: Row) -> "ClassifierRule":
        return cls(
            rule_key=row["rule_key"],
            path_pattern=row["path_pattern"],
            op_filter=json.loads(row["op_filter_json"]),
            value_filter=json.loads(row["value_filter_json"]),
            severity=row["severity"],
            category=row["category"],
            timing_sensitive=bool(row["timing_sensitive"]),
            description=row["description"],
        )

    def matches(self, context: PatchValueContext) -> bool:
        if self.op_filter and context.op not in self.op_filter:
            return False
        if not match_path(self.path_pattern, context.path):
            return False
        if "in" in self.value_filter:
            return context.new_value in set(self.value_filter["in"])
        return True


@dataclass(frozen=True)
class MaterialityEvent:
    nct_id: str
    from_version: int
    to_version: int
    submitted_date: str | None
    timing_context: str
    severity_pre_timing: str
    severity: str
    category: str
    categories: list[str]
    changed_paths: list[str]
    deterministic_rules: list[str]
    value_signals: list[dict[str, Any]]
    needs_human_review: bool
    created_at: str
    rule_set_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "nct_id": self.nct_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "submitted_date": self.submitted_date,
            "timing_context": self.timing_context,
            "severity_pre_timing": self.severity_pre_timing,
            "severity": self.severity,
            "category": self.category,
            "categories": self.categories,
            "changed_paths": self.changed_paths,
            "deterministic_rules": self.deterministic_rules,
            "value_signals": self.value_signals,
            "needs_human_review": self.needs_human_review,
            "created_at": self.created_at,
            "rule_set_hash": self.rule_set_hash,
        }


def classify_patch(
    *,
    nct_id: str,
    from_version: int,
    to_version: int,
    from_record: dict[str, Any],
    patch: list[dict[str, Any]],
    rules: list[ClassifierRule],
    submitted_date: str | None = None,
) -> MaterialityEvent | None:
    contexts = build_value_contexts(from_record, patch)
    matched_rules: list[tuple[ClassifierRule, PatchValueContext]] = []
    for context in contexts:
        for rule in rules:
            if rule.matches(context):
                matched_rules.append((rule, context))
    value_signals = collect_value_signals(contexts, from_record=from_record, patch=patch)
    matched_rules = suppress_review_metadata_rules(matched_rules)
    matched_rules = suppress_results_reconciliation_outcome_rules(matched_rules, contexts)
    matched_rules = suppress_generic_timeline_rules(matched_rules, value_signals)
    if not matched_rules and not value_signals:
        return None

    base_rank = 0
    for rule, _context in matched_rules:
        base_rank = max(base_rank, SEVERITY_RANK[rule.severity])
    for signal in value_signals:
        base_rank = max(base_rank, SEVERITY_RANK[signal["severity"]])
    severity_pre_timing = RANK_SEVERITY[base_rank]

    category = choose_category(matched_rules, value_signals)
    categories = collect_categories(matched_rules, value_signals)
    timing_context = timing_context_from_record(from_record)
    severity = apply_timing_modifier(severity_pre_timing, timing_context, category)
    deterministic_rules = sorted({rule.rule_key for rule, _context in matched_rules})
    changed_paths = sorted({context.path for context in contexts})
    return MaterialityEvent(
        nct_id=nct_id,
        from_version=from_version,
        to_version=to_version,
        submitted_date=submitted_date,
        timing_context=timing_context,
        severity_pre_timing=severity_pre_timing,
        severity=severity,
        category=category,
        categories=categories,
        changed_paths=changed_paths,
        deterministic_rules=deterministic_rules,
        value_signals=value_signals,
        needs_human_review=severity in {"high", "critical"} or timing_context == UNKNOWN,
        created_at=utc_now_iso(),
        rule_set_hash=rule_set_hash(rules),
    )


def collect_value_signals(
    contexts: list[PatchValueContext],
    *,
    from_record: dict[str, Any],
    patch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    to_record = apply_json_patch(from_record, patch)
    for context in contexts:
        if context.path == "/protocolSection/statusModule/whyStopped":
            value = "" if context.new_value is MISSING or context.new_value is None else str(context.new_value).strip()
            lower_value = value.lower()
            if not value:
                signals.append(
                    {
                        "signal": "why_stopped_empty",
                        "severity": "critical",
                        "category": "status_termination",
                        "path": context.path,
                    }
                )
            elif any(phrase in lower_value for phrase in LOW_INFORMATION_STOP_PHRASES):
                signals.append(
                    {
                        "signal": "why_stopped_low_information",
                        "severity": "high",
                        "category": "status_termination",
                        "path": context.path,
                        "value": value,
                    }
                )
        if context.path == "/protocolSection/designModule/enrollmentInfo/count":
            signal = enrollment_change_signal(context.old_value, context.new_value)
            if signal:
                signals.append(signal | {"path": context.path})
        timeline_signals = timeline_change_signals(context, from_record=from_record, to_record=to_record)
        signals.extend(timeline_signals)
    return signals


def suppress_generic_timeline_rules(
    matched_rules: list[tuple[ClassifierRule, PatchValueContext]],
    value_signals: list[dict[str, Any]],
) -> list[tuple[ClassifierRule, PatchValueContext]]:
    if not any(is_timeline_signal(signal) for signal in value_signals):
        return matched_rules
    return [(rule, context) for rule, context in matched_rules if rule.category != TIMELINE_RULE_CATEGORY]


def suppress_review_metadata_rules(
    matched_rules: list[tuple[ClassifierRule, PatchValueContext]],
) -> list[tuple[ClassifierRule, PatchValueContext]]:
    return [(rule, context) for rule, context in matched_rules if not is_review_metadata_path(context.path)]


def suppress_results_reconciliation_outcome_rules(
    matched_rules: list[tuple[ClassifierRule, PatchValueContext]],
    contexts: list[PatchValueContext],
) -> list[tuple[ClassifierRule, PatchValueContext]]:
    if not is_results_reconciliation_patch(contexts):
        return matched_rules
    return [
        (rule, context)
        for rule, context in matched_rules
        if rule.category not in OUTCOME_CHANGE_CATEGORIES
    ]


def is_review_metadata_path(path: str) -> bool:
    return path == "/reviewUnit" or "/reviewUnit" in path


def is_results_reconciliation_patch(contexts: list[PatchValueContext]) -> bool:
    for context in contexts:
        if context.path == "/hasResults" and context.new_value is True:
            return True
        if context.path == "/resultsSection" and context.op in {"add", "replace"}:
            return True
        if context.path.startswith("/resultsSection/") and context.op in {"add", "replace"}:
            return True
    return False


def is_timeline_signal(signal: dict[str, Any]) -> bool:
    return str(signal.get("signal", "")).startswith("timeline_") or signal.get("signal") == "milestone_realized"


def enrollment_change_signal(old_value: Any, new_value: Any) -> dict[str, Any] | None:
    if not isinstance(old_value, (int, float)) or not isinstance(new_value, (int, float)):
        return None
    if old_value == 0:
        return None
    if old_value > 0 and new_value == 0:
        return {
            "signal": "enrollment_zeroed",
            "severity": "critical",
            "category": "enrollment_change",
            "old_value": old_value,
            "new_value": new_value,
            "pct_change": 1.0,
        }
    pct_change = abs(new_value - old_value) / abs(old_value)
    if pct_change >= 0.2:
        return {
            "signal": "enrollment_count_change_ge_20pct",
            "severity": "high",
            "category": "enrollment_change",
            "old_value": old_value,
            "new_value": new_value,
            "pct_change": round(pct_change, 4),
        }
    return None


@dataclass(frozen=True)
class ParsedCtgovDate:
    value: date
    precision: str


def timeline_change_signals(
    context: PatchValueContext,
    *,
    from_record: dict[str, Any],
    to_record: dict[str, Any],
) -> list[dict[str, Any]]:
    struct_pointer = timeline_struct_pointer(context.path)
    if not struct_pointer:
        return []
    leaf = timeline_leaf(context.path, struct_pointer)
    signals: list[dict[str, Any]] = []
    if leaf in {"", "date"}:
        old_date = context.old_value if leaf == "date" else struct_field(context.old_value, "date")
        new_date = context.new_value if leaf == "date" else struct_field(context.new_value, "date")
        signal = timeline_date_signal(
            path=context.path,
            struct_pointer=struct_pointer,
            old_date=old_date,
            new_date=new_date,
            old_type=resolve_pointer(from_record, f"{struct_pointer}/type"),
            new_type=resolve_pointer(to_record, f"{struct_pointer}/type"),
            timing_context=timing_context_from_record(from_record),
        )
        if signal:
            signals.append(signal)
    if leaf in {"", "type"}:
        old_type = context.old_value if leaf == "type" else struct_field(context.old_value, "type")
        new_type = context.new_value if leaf == "type" else struct_field(context.new_value, "type")
        signal = milestone_realized_signal(
            path=context.path,
            struct_pointer=struct_pointer,
            old_type=old_type,
            new_type=new_type,
            old_date=resolve_pointer(from_record, f"{struct_pointer}/date"),
            new_date=resolve_pointer(to_record, f"{struct_pointer}/date"),
        )
        if signal:
            signals.append(signal)
    return signals


def timeline_struct_pointer(path: str) -> str | None:
    for struct_pointer in TIMELINE_DATE_STRUCTS:
        if path == struct_pointer or path.startswith(f"{struct_pointer}/"):
            return struct_pointer
    return None


def timeline_leaf(path: str, struct_pointer: str) -> str:
    if path == struct_pointer:
        return ""
    return path.removeprefix(f"{struct_pointer}/").split("/", maxsplit=1)[0]


def struct_field(value: Any, key: str) -> Any:
    if value is MISSING or not isinstance(value, dict):
        return MISSING
    return value.get(key, MISSING)


def timeline_date_signal(
    *,
    path: str,
    struct_pointer: str,
    old_date: Any,
    new_date: Any,
    old_type: Any,
    new_type: Any,
    timing_context: str,
) -> dict[str, Any] | None:
    if old_date is MISSING and new_date is MISSING:
        return None
    if old_date == new_date:
        return None
    old_parsed = parse_ctgov_date(old_date)
    new_parsed = parse_ctgov_date(new_date)
    base_signal = {
        "path": path,
        "date_struct": struct_pointer.rsplit("/", maxsplit=1)[-1],
        "old_value": None if old_date is MISSING else old_date,
        "new_value": None if new_date is MISSING else new_date,
    }
    if old_parsed and new_parsed:
        raw_delta_days = (new_parsed.value - old_parsed.value).days
        delta_days = abs(raw_delta_days)
        if normalized_type(old_type) in ACTUAL_DATE_TYPES and normalized_type(new_type) in ACTUAL_DATE_TYPES:
            signal = {
                "signal": "timeline_actual_date_correction",
                "severity": "low",
                "category": "timeline_actual_date_correction",
            }
        elif (
            normalized_type(old_type) in ANTICIPATED_DATE_TYPES
            and normalized_type(new_type) in ACTUAL_DATE_TYPES
            and raw_delta_days < 0
        ):
            signal = {
                "signal": "timeline_actualized_earlier",
                "severity": "low",
                "category": "timeline_actualized_earlier",
            }
        else:
            signal = timeline_delta_signal(
                delta_days,
                direction=timeline_direction(raw_delta_days),
                timing_context=timing_context,
            )
        return base_signal | signal | {
            "delta_days": delta_days,
            "direction": timeline_direction(raw_delta_days),
            "old_type": None if old_type is MISSING else old_type,
            "new_type": None if new_type is MISSING else new_type,
            "old_precision": old_parsed.precision,
            "new_precision": new_parsed.precision,
        }
    return base_signal | {
        "signal": "timeline_shift",
        "severity": "medium",
        "category": "timeline_shift",
        "direction": "unknown",
        "old_type": None if old_type is MISSING else old_type,
        "new_type": None if new_type is MISSING else new_type,
        "reason": "date_unparsed_or_missing",
    }


def parse_ctgov_date(value: Any) -> ParsedCtgovDate | None:
    if not isinstance(value, str):
        return None
    parts = value.strip().split("-")
    try:
        if len(parts) == 3:
            return ParsedCtgovDate(date(int(parts[0]), int(parts[1]), int(parts[2])), "day")
        if len(parts) == 2:
            return ParsedCtgovDate(date(int(parts[0]), int(parts[1]), 1), "month")
        if len(parts) == 1 and len(parts[0]) == 4:
            return ParsedCtgovDate(date(int(parts[0]), 1, 1), "year")
    except ValueError:
        return None
    return None


def timeline_delta_signal(delta_days: int, *, direction: str, timing_context: str) -> dict[str, Any]:
    if delta_days < 30:
        return {
            "signal": "timeline_minor_adjustment",
            "severity": "low",
            "category": "timeline_minor_adjustment",
        }
    if direction == "earlier":
        if delta_days <= 365:
            return {
                "signal": "timeline_earlier_adjustment",
                "severity": "low",
                "category": "timeline_minor_adjustment",
            }
        return {
            "signal": "timeline_earlier_shift",
            "severity": "medium",
            "category": "timeline_shift",
        }
    if delta_days <= 90:
        return {
            "signal": "timeline_shift",
            "severity": "medium",
            "category": "timeline_shift",
        }
    if delta_days <= 365:
        return {
            "signal": "timeline_significant_shift",
            "severity": "medium",
            "category": "timeline_significant_shift",
        }
    if timing_context not in {LATE_RECRUITMENT, POST_RECRUITMENT}:
        return {
            "signal": "timeline_major_slip",
            "severity": "medium",
            "category": "timeline_major_slip",
        }
    return {
        "signal": "timeline_major_slip",
        "severity": "high",
        "category": "timeline_major_slip",
    }


def timeline_direction(raw_delta_days: int) -> str:
    if raw_delta_days > 0:
        return "later"
    if raw_delta_days < 0:
        return "earlier"
    return "same"


def milestone_realized_signal(
    *,
    path: str,
    struct_pointer: str,
    old_type: Any,
    new_type: Any,
    old_date: Any,
    new_date: Any,
) -> dict[str, Any] | None:
    if normalized_type(old_type) not in ANTICIPATED_DATE_TYPES:
        return None
    if normalized_type(new_type) not in ACTUAL_DATE_TYPES:
        return None
    old_parsed = parse_ctgov_date(old_date)
    new_parsed = parse_ctgov_date(new_date)
    if old_parsed and new_parsed:
        delta_days: int | None = abs((new_parsed.value - old_parsed.value).days)
        if delta_days >= 30:
            return None
    else:
        delta_days = None
        if old_date != new_date:
            return None
    return {
        "signal": "milestone_realized",
        "severity": "low",
        "category": "milestone_realized",
        "path": path,
        "date_struct": struct_pointer.rsplit("/", maxsplit=1)[-1],
        "old_type": old_type,
        "new_type": new_type,
        "old_date": None if old_date is MISSING else old_date,
        "new_date": None if new_date is MISSING else new_date,
        "delta_days": delta_days,
    }


def normalized_type(value: Any) -> str:
    if value is MISSING or value is None:
        return ""
    return str(value).strip().upper()


def choose_category(
    matched_rules: list[tuple[ClassifierRule, PatchValueContext]],
    value_signals: list[dict[str, Any]],
) -> str:
    candidates = [(rule.severity, rule.category) for rule, _context in matched_rules]
    candidates.extend((signal["severity"], signal_category(signal)) for signal in value_signals)
    if candidates:
        return sorted(
            candidates,
            key=lambda item: (SEVERITY_RANK[item[0]], category_priority(item[1])),
            reverse=True,
        )[0][1]
    return "unknown_material_change"


def collect_categories(
    matched_rules: list[tuple[ClassifierRule, PatchValueContext]],
    value_signals: list[dict[str, Any]],
) -> list[str]:
    categories = {rule.category for rule, _context in matched_rules}
    for signal in value_signals:
        categories.add(signal_category(signal))
    return sorted(categories, key=lambda category: category_priority(category), reverse=True)


def signal_category(signal: dict[str, Any]) -> str:
    return signal.get("category") or "status_termination"


def category_priority(category: str) -> int:
    priority = {
        "primary_outcome_change": 100,
        "design_change": 90,
        "arm_intervention_change": 85,
        "serious_adverse_event_removal": 82,
        "status_termination": 80,
        "secondary_outcome_change": 70,
        "serious_adverse_event_addition": 68,
        "serious_adverse_event_modification": 67,
        "eligibility_change": 60,
        "adverse_event_group_change": 58,
        "other_adverse_event_removal": 56,
        "enrollment_change": 50,
        "timeline_major_slip": 45,
        "timeline_significant_shift": 44,
        "timeline_shift": 40,
        "timeline_minor_adjustment": 30,
        "timeline_actual_date_correction": 28,
        "timeline_actualized_earlier": 27,
        "milestone_realized": 25,
        "other_adverse_event_addition": 22,
        "other_adverse_event_modification": 21,
    }
    return priority.get(category, 0)


def apply_timing_modifier(severity: str, timing_context: str, category: str) -> str:
    if timing_context not in {LATE_RECRUITMENT, POST_RECRUITMENT}:
        return severity
    if category not in TIMING_SENSITIVE_CATEGORIES:
        return severity
    return RANK_SEVERITY[min(SEVERITY_RANK[severity] + 1, SEVERITY_RANK["critical"])]


def provenance_for_event(event: MaterialityEvent) -> Provenance:
    payload = event.as_dict()
    return Provenance.from_payload(
        source=Source.DERIVED_CLASSIFIER,
        source_url="trialdiff://classifier/materiality",
        payload=payload,
        source_version=sha256_json(payload),
    )


def rule_set_hash(rules: list[ClassifierRule]) -> str:
    payload = [
        {
            "rule_key": rule.rule_key,
            "path_pattern": rule.path_pattern,
            "op_filter": rule.op_filter,
            "value_filter": rule.value_filter,
            "severity": rule.severity,
            "category": rule.category,
            "timing_sensitive": rule.timing_sensitive,
            "description": rule.description,
        }
        for rule in sorted(rules, key=lambda item: item.rule_key)
    ]
    return sha256_json(payload)
