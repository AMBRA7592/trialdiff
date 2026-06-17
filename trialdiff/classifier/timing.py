from __future__ import annotations

from typing import Any

from trialdiff.jsonpatch import resolve_pointer


PRE_RECRUITMENT = "pre_recruitment"
EARLY_RECRUITMENT = "early_recruitment"
LATE_RECRUITMENT = "late_recruitment"
POST_RECRUITMENT = "post_recruitment"
UNKNOWN = "unknown"


def timing_context_from_record(record: dict[str, Any]) -> str:
    status = resolve_pointer(record, "/protocolSection/statusModule/overallStatus")
    if not isinstance(status, str):
        return UNKNOWN
    return timing_context_from_status(status)


def timing_context_from_status(status: str) -> str:
    normalized = status.upper()
    if normalized in {"NOT_YET_RECRUITING", "WITHDRAWN"}:
        return PRE_RECRUITMENT
    if normalized in {"RECRUITING", "ENROLLING_BY_INVITATION"}:
        return EARLY_RECRUITMENT
    if normalized == "ACTIVE_NOT_RECRUITING":
        return LATE_RECRUITMENT
    if normalized in {"COMPLETED", "TERMINATED", "SUSPENDED"}:
        return POST_RECRUITMENT
    return UNKNOWN
