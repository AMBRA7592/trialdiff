from __future__ import annotations

from typing import Any

from trialdiff.provenance import sha256_json


EVENT_CLASS_VERSION = "trialdiff.event_classes.v0.1"

PRIMARY_ENDPOINT_CLEAN = "primary_endpoint_changed_after_primary_completion_without_results_reconciliation"
SECONDARY_OUTCOME_REMOVED = "secondary_outcome_removed_after_primary_completion"
ENROLLMENT_CHANGED_TO_ZERO = "enrollment_changed_to_zero"
WHY_STOPPED_REMOVED_TERMINAL = "why_stopped_removed_in_terminal_context"
OUTCOME_EDIT_WITH_RESULTS_SIGNAL = "outcome_edit_cooccurs_with_results_posting"

EVENT_CLASS_DEFINITIONS: dict[str, str] = {
    PRIMARY_ENDPOINT_CLEAN: (
        "FROM-version is completed or has actual primary completion; a primary outcome measure, "
        "description, timeFrame, or whole primary-outcome item changed; no hasResults/resultsSection "
        "co-occurrence signal is present."
    ),
    SECONDARY_OUTCOME_REMOVED: (
        "FROM-version is completed or has actual primary completion; a whole secondaryOutcomes item is "
        "removed; when a TO-version outcome list is available, the normalized removed outcome does not "
        "reappear elsewhere in that list."
    ),
    ENROLLMENT_CHANGED_TO_ZERO: "Enrollment count changes from a positive value to exactly zero.",
    WHY_STOPPED_REMOVED_TERMINAL: (
        "FROM-version whyStopped is nonempty; TO-version whyStopped is empty or absent; FROM or TO status "
        "is TERMINATED, WITHDRAWN, or SUSPENDED."
    ),
    OUTCOME_EDIT_WITH_RESULTS_SIGNAL: (
        "A primary or secondary outcome path changed and the same patch carries a hasResults or "
        "resultsSection co-occurrence signal."
    ),
}

EVENT_CLASS_RULE_SET_HASH = sha256_json(
    {"version": EVENT_CLASS_VERSION, "definitions": EVENT_CLASS_DEFINITIONS}
)

COMPLETED_STATUSES = {"COMPLETED"}
TERMINAL_STATUSES = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}


def event_classes_for_patch(
    *,
    from_record: dict[str, Any],
    to_record: dict[str, Any] | None,
    patch: list[dict[str, Any]],
) -> list[str]:
    classes: list[str] = []
    reconciliation_signal = has_results_reconciliation_signal(
        from_record=from_record,
        to_record=to_record,
        patch=patch,
    )
    if (
        after_primary_completion(from_record)
        and not reconciliation_signal
        and primary_endpoint_definition_changed(from_record, to_record, patch)
    ):
        classes.append(PRIMARY_ENDPOINT_CLEAN)
    if after_primary_completion(from_record) and secondary_outcome_item_removed_without_reindex(
        from_record,
        to_record,
        patch,
    ):
        classes.append(SECONDARY_OUTCOME_REMOVED)
    if enrollment_changed_to_zero(from_record, to_record):
        classes.append(ENROLLMENT_CHANGED_TO_ZERO)
    if why_stopped_removed_in_terminal_context(from_record, to_record):
        classes.append(WHY_STOPPED_REMOVED_TERMINAL)
    if reconciliation_signal and any(is_outcome_path(operation.get("path", "")) for operation in patch):
        classes.append(OUTCOME_EDIT_WITH_RESULTS_SIGNAL)
    return classes


def combined_rule_set_hash(*, triage_rule_set_hash: str | None) -> str:
    return sha256_json(
        {
            "triage_rule_set_hash": triage_rule_set_hash or "",
            "event_class_rule_set_hash": EVENT_CLASS_RULE_SET_HASH,
        }
    )


def has_results_reconciliation_signal(
    *,
    from_record: dict[str, Any],
    to_record: dict[str, Any] | None,
    patch: list[dict[str, Any]],
) -> bool:
    for operation in patch:
        path = operation.get("path", "")
        if path == "/hasResults" or path.startswith("/resultsSection"):
            return True
    return not bool(from_record.get("hasResults")) and bool((to_record or {}).get("hasResults"))


def after_primary_completion(record: dict[str, Any]) -> bool:
    return primary_completion_actual(record) or overall_status(record) in COMPLETED_STATUSES


def primary_completion_actual(record: dict[str, Any]) -> bool:
    return (
        get_path(record, ["protocolSection", "statusModule", "primaryCompletionDateStruct", "type"])
        == "ACTUAL"
    )


def primary_endpoint_definition_changed(
    from_record: dict[str, Any],
    to_record: dict[str, Any] | None,
    patch: list[dict[str, Any]],
) -> bool:
    for operation in patch:
        path = operation.get("path", "")
        if not (is_primary_endpoint_definition_path(path) or is_primary_endpoint_item_path(path)):
            continue
        parts = pointer_parts(path)
        if to_record is None:
            if operation.get("op") in {"add", "remove", "replace"}:
                return True
            continue
        if get_path(from_record, parts) != get_path(to_record, parts):
            return True
    return False


def secondary_outcome_item_removed_without_reindex(
    from_record: dict[str, Any],
    to_record: dict[str, Any] | None,
    patch: list[dict[str, Any]],
) -> bool:
    removed_operations = [operation for operation in patch if is_secondary_outcome_item_removal(operation)]
    if not removed_operations:
        return False
    if to_record is None:
        return True
    to_outcomes = (
        get_path(to_record, ["protocolSection", "outcomesModule", "secondaryOutcomes"], [])
        or []
    )
    to_normalized = {normalize_outcome(outcome) for outcome in to_outcomes}
    for operation in removed_operations:
        removed = get_path(from_record, pointer_parts(operation["path"]))
        normalized = normalize_outcome(removed)
        if normalized and normalized not in to_normalized:
            return True
    return False


def enrollment_changed_to_zero(from_record: dict[str, Any], to_record: dict[str, Any] | None) -> bool:
    from_count = get_path(from_record, ["protocolSection", "designModule", "enrollmentInfo", "count"])
    to_count = get_path(to_record, ["protocolSection", "designModule", "enrollmentInfo", "count"])
    try:
        return from_count is not None and int(from_count) > 0 and to_count is not None and int(to_count) == 0
    except (TypeError, ValueError):
        return False


def why_stopped_removed_in_terminal_context(
    from_record: dict[str, Any],
    to_record: dict[str, Any] | None,
) -> bool:
    from_why_stopped = get_path(from_record, ["protocolSection", "statusModule", "whyStopped"])
    to_why_stopped = get_path(to_record, ["protocolSection", "statusModule", "whyStopped"])
    if not (from_why_stopped and str(from_why_stopped).strip()):
        return False
    if to_why_stopped and str(to_why_stopped).strip():
        return False
    return overall_status(from_record) in TERMINAL_STATUSES or overall_status(to_record) in TERMINAL_STATUSES


def overall_status(record: dict[str, Any]) -> str | None:
    return get_path(record, ["protocolSection", "statusModule", "overallStatus"])


def is_primary_endpoint_definition_path(path: str) -> bool:
    parts = pointer_parts(path)
    return (
        len(parts) >= 5
        and parts[0:3] == ["protocolSection", "outcomesModule", "primaryOutcomes"]
        and parts[4] in {"measure", "description", "timeFrame"}
    )


def is_primary_endpoint_item_path(path: str) -> bool:
    parts = pointer_parts(path)
    return (
        len(parts) == 4
        and parts[0:3] == ["protocolSection", "outcomesModule", "primaryOutcomes"]
        and parts[3].isdigit()
    )


def is_secondary_outcome_item_removal(operation: dict[str, Any]) -> bool:
    if operation.get("op") != "remove":
        return False
    parts = pointer_parts(operation.get("path", ""))
    return (
        len(parts) == 4
        and parts[0:3] == ["protocolSection", "outcomesModule", "secondaryOutcomes"]
        and parts[3].isdigit()
    )


def is_outcome_path(path: str) -> bool:
    return path.startswith("/protocolSection/outcomesModule/primaryOutcomes") or path.startswith(
        "/protocolSection/outcomesModule/secondaryOutcomes"
    )


def normalize_outcome(value: Any) -> tuple[str, str, str] | None:
    if not isinstance(value, dict):
        return None
    return tuple(str(value.get(key) or "").strip().lower() for key in ("measure", "description", "timeFrame"))


def pointer_parts(path: str) -> list[str]:
    if not path:
        return []
    return [part.replace("~1", "/").replace("~0", "~") for part in path.split("/")[1:]]


def get_path(value: Any, parts: list[str], default: Any = None) -> Any:
    current = value
    for part in parts:
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return default
        elif isinstance(current, dict):
            if part not in current:
                return default
            current = current[part]
        else:
            return default
    return current
