from enum import StrEnum


class Source(StrEnum):
    OFFICIAL_V2 = "official_v2"
    CLINICALTRIALS_RSS = "clinicaltrials_rss"
    CTGOV_INTERNAL_HISTORY = "ctgov_internal_history"
    SELF_SNAPSHOT = "self_snapshot"
    MANUAL_CASE_STUDY = "manual_case_study"
    DERIVED_CLASSIFIER = "derived_classifier"
    DERIVED_EVIDENCE_RECORD = "derived_evidence_record"
    LLM_SUMMARY = "llm_summary"


class PatchKind(StrEnum):
    CTGOV_HISTORY_PATCH = "ctgov_history_patch"
    SELF_SNAPSHOT_PATCH = "self_snapshot_patch"
