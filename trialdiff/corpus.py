from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import time
from typing import Any

from trialdiff.fetchers.internal import ClinicalTrialsInternalHistoryClient
from trialdiff.fetchers.official import ClinicalTrialsOfficialClient
from trialdiff.provenance import utc_now_iso


DEFAULT_ALLOWED_PHASES = {"PHASE2", "PHASE3"}


@dataclass(frozen=True)
class CorpusStudy:
    nct_id: str
    title: str | None
    lead_sponsor: str | None
    phases: list[str]
    status: str | None
    last_update_posted: str | None
    version_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "nct_id": self.nct_id,
            "title": self.title,
            "lead_sponsor": self.lead_sponsor,
            "phases": self.phases,
            "status": self.status,
            "last_update_posted": self.last_update_posted,
            "version_count": self.version_count,
        }


@dataclass(frozen=True)
class CorpusSelection:
    name: str
    generated_at: str
    query: dict[str, Any]
    filters: dict[str, Any]
    relaxation: dict[str, Any]
    candidate_count: int
    locally_eligible_count: int
    selected: list[CorpusStudy]
    errors: list[dict[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "generated_at": self.generated_at,
            "query": self.query,
            "filters": self.filters,
            "relaxation": self.relaxation,
            "candidate_count": self.candidate_count,
            "locally_eligible_count": self.locally_eligible_count,
            "selected_count": len(self.selected),
            "selected_nct_ids": [study.nct_id for study in self.selected],
            "studies": [study.as_dict() for study in self.selected],
            "errors": self.errors,
        }


def select_breast_cancer_corpus(
    *,
    official_client: ClinicalTrialsOfficialClient | None = None,
    internal_client: ClinicalTrialsInternalHistoryClient | None = None,
    limit: int = 100,
    query_cond: str = "breast cancer",
    cutoff_date: str = "2021-05-20",
    min_versions: int = 3,
    allowed_phases: set[str] | None = None,
    page_size: int = 100,
    max_pages: int = 25,
    delay_seconds: float = 0.25,
) -> CorpusSelection:
    official_client = official_client or ClinicalTrialsOfficialClient()
    internal_client = internal_client or ClinicalTrialsInternalHistoryClient()
    allowed = allowed_phases or DEFAULT_ALLOWED_PHASES
    candidates: list[dict[str, Any]] = []
    locally_eligible: list[dict[str, Any]] = []
    selected: list[CorpusStudy] = []
    errors: list[dict[str, str]] = []
    page_token: str | None = None

    for _page in range(max_pages):
        payload, _url = official_client.search_studies(
            query_cond=query_cond,
            page_size=page_size,
            page_token=page_token,
            fields=None,
        )
        studies = payload.get("studies") or []
        candidates.extend(studies)
        for study in studies:
            if locally_matches(study, cutoff_date=cutoff_date, allowed_phases=allowed):
                locally_eligible.append(study)
                nct_id = get_nct_id(study)
                if not nct_id:
                    continue
                try:
                    history_payload, _history_url = internal_client.fetch_history_summary(nct_id)
                    version_count = len(((history_payload.get("history") or {}).get("changes") or []))
                except Exception as exc:
                    errors.append({"nct_id": nct_id, "error": str(exc)})
                    continue
                if version_count >= min_versions:
                    selected.append(corpus_study_from_record(study, version_count))
                    if len(selected) >= limit:
                        return build_selection(
                            selected=selected,
                            errors=errors,
                            query_cond=query_cond,
                            cutoff_date=cutoff_date,
                            min_versions=min_versions,
                            allowed_phases=allowed,
                            candidate_count=len(candidates),
                            locally_eligible_count=len(locally_eligible),
                            max_pages=max_pages,
                            limit=limit,
                        )
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return build_selection(
        selected=selected,
        errors=errors,
        query_cond=query_cond,
        cutoff_date=cutoff_date,
        min_versions=min_versions,
        allowed_phases=allowed,
        candidate_count=len(candidates),
        locally_eligible_count=len(locally_eligible),
        max_pages=max_pages,
        limit=limit,
    )


def build_selection(
    *,
    selected: list[CorpusStudy],
    errors: list[dict[str, str]],
    query_cond: str,
    cutoff_date: str,
    min_versions: int,
    allowed_phases: set[str],
    candidate_count: int,
    locally_eligible_count: int,
    max_pages: int,
    limit: int,
) -> CorpusSelection:
    return CorpusSelection(
        name="breast_cancer_phase2_3",
        generated_at=utc_now_iso(),
        query={
            "endpoint": "/api/v2/studies",
            "query.cond": query_cond,
            "max_pages": max_pages,
            "limit": limit,
        },
        filters={
            "study_type": "INTERVENTIONAL",
            "allowed_phases": sorted(allowed_phases),
            "last_update_posted_gte": cutoff_date,
            "min_versions": min_versions,
        },
        relaxation={},
        candidate_count=candidate_count,
        locally_eligible_count=locally_eligible_count,
        selected=selected,
        errors=errors,
    )


def locally_matches(study: dict[str, Any], *, cutoff_date: str, allowed_phases: set[str]) -> bool:
    protocol = study.get("protocolSection") or {}
    design = protocol.get("designModule") or {}
    status = protocol.get("statusModule") or {}
    if design.get("studyType") != "INTERVENTIONAL":
        return False
    phases = set(design.get("phases") or [])
    if not phases.intersection(allowed_phases):
        return False
    update_date = (status.get("lastUpdatePostDateStruct") or {}).get("date")
    if not update_date:
        return False
    return update_date >= cutoff_date


def corpus_study_from_record(study: dict[str, Any], version_count: int) -> CorpusStudy:
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    sponsor = protocol.get("sponsorCollaboratorsModule") or {}
    status = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    return CorpusStudy(
        nct_id=identification["nctId"],
        title=identification.get("briefTitle"),
        lead_sponsor=(sponsor.get("leadSponsor") or {}).get("name"),
        phases=design.get("phases") or [],
        status=status.get("overallStatus"),
        last_update_posted=(status.get("lastUpdatePostDateStruct") or {}).get("date"),
        version_count=version_count,
    )


def get_nct_id(study: dict[str, Any]) -> str | None:
    return ((study.get("protocolSection") or {}).get("identificationModule") or {}).get("nctId")


def write_corpus(selection: CorpusSelection, output_dir: str | Path, stem: str | None = None) -> tuple[Path, Path]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    date_suffix = date.today().isoformat().replace("-", "")
    file_stem = stem or f"{selection.name}_{date_suffix}"
    json_path = path / f"{file_stem}.json"
    txt_path = path / f"{file_stem}.txt"
    json_path.write_text(json.dumps(selection.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    txt_path.write_text("\n".join(study.nct_id for study in selection.selected) + "\n", encoding="utf-8")
    return json_path, txt_path
