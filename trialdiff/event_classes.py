from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from trialdiff.jsonpatch import JsonPatchError, apply_patch, build_value_contexts
from trialdiff.provenance import sha256_json
from trialdiff.ruleset import implementation_source_hash


EVENT_CLASS_VERSION = "trialdiff.event_classes.v0.3"

PRIMARY_ENDPOINT_CLEAN = "primary_endpoint_changed_after_primary_completion_without_results_reconciliation"
SECONDARY_OUTCOME_REMOVED = "secondary_outcome_removed_after_primary_completion"
ENROLLMENT_CHANGED_TO_ZERO = "enrollment_changed_to_zero"
WHY_STOPPED_REMOVED_TERMINAL = "why_stopped_removed_in_terminal_context"
OUTCOME_EDIT_WITH_RESULTS_SIGNAL = "outcome_edit_cooccurs_with_results_posting"

EVENT_CLASS_DEFINITIONS: dict[str, str] = {
    PRIMARY_ENDPOINT_CLEAN: (
        "FROM-version is completed or has actual primary completion; a primary outcome measure, "
        "description, timeFrame, or whole primary-outcome item changed between the FROM-version record "
        "and the TO-version reconstructed by sequential replay of the adjacent-version patch; a pure "
        "reordering of otherwise identical primary-outcome definitions does not count as a definition "
        "change; no hasResults/resultsSection co-occurrence signal is present."
    ),
    SECONDARY_OUTCOME_REMOVED: (
        "FROM-version is completed or has actual primary completion; a whole secondaryOutcomes item is "
        "removed, with each removal target resolved against the evolving document during sequential "
        "patch replay; the normalized removed outcome does not reappear elsewhere in the reconstructed "
        "TO-version outcome list."
    ),
    ENROLLMENT_CHANGED_TO_ZERO: (
        "Enrollment count changes from a positive value in the FROM-version record to exactly zero in "
        "the TO-version reconstructed by sequential replay of the adjacent-version patch."
    ),
    WHY_STOPPED_REMOVED_TERMINAL: (
        "FROM-version whyStopped is nonempty; the TO-version reconstructed by sequential replay of the "
        "adjacent-version patch shows whyStopped empty or absent; FROM or TO status is TERMINATED, "
        "WITHDRAWN, or SUSPENDED. Replay failure blocks classification rather than counting as removal."
    ),
    OUTCOME_EDIT_WITH_RESULTS_SIGNAL: (
        "A primary or secondary outcome path changed and the same patch carries a hasResults or "
        "resultsSection co-occurrence signal."
    ),
}

_TRIALDIFF_DIR = Path(__file__).resolve().parent
EVENT_CLASS_IMPLEMENTATION_HASH = implementation_source_hash(
    {
        "trialdiff.event_classes": Path(__file__),
        "trialdiff.jsonpatch": _TRIALDIFF_DIR / "jsonpatch.py",
        "trialdiff.ruleset": _TRIALDIFF_DIR / "ruleset.py",
    }
)
EVENT_CLASS_RULE_SET_HASH = sha256_json(
    {
        "version": EVENT_CLASS_VERSION,
        "definitions": EVENT_CLASS_DEFINITIONS,
        "implementation_hash": EVENT_CLASS_IMPLEMENTATION_HASH,
    }
)

COMPLETED_STATUSES = {"COMPLETED"}
TERMINAL_STATUSES = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}
SUPPORTED_PATCH_OPERATIONS = frozenset({"add", "remove", "replace"})


class EventClassInputError(ValueError):
    """The source pair and patch cannot safely support event classification."""


def validate_patch_operations(patch: list[dict[str, Any]]) -> None:
    if not isinstance(patch, list):
        raise EventClassInputError("Patch must be a list of operations")
    for index, operation in enumerate(patch):
        if not isinstance(operation, dict):
            raise EventClassInputError(f"Patch operation {index} must be an object")
        op = operation.get("op")
        if op not in SUPPORTED_PATCH_OPERATIONS:
            raise EventClassInputError(f"Patch operation {index} uses unsupported op {op!r}")
        path = operation.get("path")
        if not isinstance(path, str):
            raise EventClassInputError(f"Patch operation {index} must carry a string path")
        if op in {"add", "replace"} and "value" not in operation:
            raise EventClassInputError(f"Patch operation {index} with op {op!r} must carry a value")


def derive_to_record(
    from_record: dict[str, Any],
    to_record: dict[str, Any] | None,
    patch: list[dict[str, Any]],
) -> dict[str, Any]:
    # Replay is the authoritative TO view. A stored snapshot is an independent
    # consistency check, never a substitute for a patch that cannot replay.
    validate_patch_operations(patch)
    try:
        derived_to_record = apply_patch(from_record, patch)
    except (JsonPatchError, KeyError, IndexError, TypeError, ValueError) as error:
        raise EventClassInputError(f"Patch replay failed: {error}") from error
    if to_record is not None and derived_to_record != to_record:
        raise EventClassInputError("Stored TO-version record does not equal sequential patch replay")
    return derived_to_record


def event_classes_for_patch(
    *,
    from_record: dict[str, Any],
    to_record: dict[str, Any] | None,
    patch: list[dict[str, Any]],
) -> list[str]:
    to_record = derive_to_record(from_record, to_record, patch)
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
    return sorted(classes)


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
    to_record: dict[str, Any],
    patch: list[dict[str, Any]],
) -> bool:
    for operation in patch:
        path = operation.get("path", "")
        if path == "/hasResults" or path.startswith("/resultsSection"):
            return True
    if bool(from_record.get("hasResults")) != bool(to_record.get("hasResults")):
        raise EventClassInputError("hasResults changed without a corresponding patch operation")
    return False


def after_primary_completion(record: dict[str, Any]) -> bool:
    return primary_completion_actual(record) or overall_status(record) in COMPLETED_STATUSES


def primary_completion_actual(record: dict[str, Any]) -> bool:
    return (
        get_path(record, ["protocolSection", "statusModule", "primaryCompletionDateStruct", "type"])
        == "ACTUAL"
    )


def primary_endpoint_definition_changed(
    from_record: dict[str, Any],
    to_record: dict[str, Any],
    patch: list[dict[str, Any]],
) -> bool:
    relevant_operation = any(
        is_primary_endpoint_definition_path(operation.get("path", ""))
        or is_primary_endpoint_item_path(operation.get("path", ""))
        for operation in patch
    )
    return relevant_operation and primary_endpoint_definitions(from_record) != primary_endpoint_definitions(to_record)


def primary_endpoint_definitions(
    record: dict[str, Any],
) -> Counter[tuple[str | None, str | None, str | None]]:
    outcomes = get_path(record, ["protocolSection", "outcomesModule", "primaryOutcomes"], [])
    if outcomes is None:
        outcomes = []
    if not isinstance(outcomes, list):
        raise EventClassInputError("primaryOutcomes must be an array")
    definitions: Counter[tuple[str | None, str | None, str | None]] = Counter()
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            raise EventClassInputError(f"primaryOutcomes item {index} must be an object")
        definition = tuple(outcome.get(key) for key in ("measure", "description", "timeFrame"))
        if any(value is not None and not isinstance(value, str) for value in definition):
            raise EventClassInputError(f"primaryOutcomes item {index} has a non-string definition field")
        definitions[definition] += 1
    return definitions


def secondary_outcome_item_removed_without_reindex(
    from_record: dict[str, Any],
    to_record: dict[str, Any],
    patch: list[dict[str, Any]],
) -> bool:
    if not any(is_secondary_outcome_item_removal(operation) for operation in patch):
        return False
    removed_contexts = [
        context
        for context in build_value_contexts(from_record, patch)
        if is_secondary_outcome_item_removal({"op": context.op, "path": context.path})
    ]
    to_outcomes = get_path(to_record, ["protocolSection", "outcomesModule", "secondaryOutcomes"], [])
    if to_outcomes is None:
        to_outcomes = []
    if not isinstance(to_outcomes, list):
        raise EventClassInputError("secondaryOutcomes must be an array")
    to_normalized = {normalize_outcome(outcome) for outcome in to_outcomes}
    for context in removed_contexts:
        normalized = normalize_outcome(context.old_value)
        if normalized and normalized not in to_normalized:
            return True
    return False


def enrollment_changed_to_zero(from_record: dict[str, Any], to_record: dict[str, Any]) -> bool:
    from_count = get_path(from_record, ["protocolSection", "designModule", "enrollmentInfo", "count"])
    to_count = get_path(to_record, ["protocolSection", "designModule", "enrollmentInfo", "count"])
    try:
        return from_count is not None and int(from_count) > 0 and to_count is not None and int(to_count) == 0
    except (TypeError, ValueError):
        return False


def why_stopped_removed_in_terminal_context(
    from_record: dict[str, Any],
    to_record: dict[str, Any],
) -> bool:
    from_why_stopped = get_path(from_record, ["protocolSection", "statusModule", "whyStopped"])
    if not (from_why_stopped and str(from_why_stopped).strip()):
        return False
    to_why_stopped = get_path(to_record, ["protocolSection", "statusModule", "whyStopped"])
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
