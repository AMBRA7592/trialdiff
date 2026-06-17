from __future__ import annotations

from typing import Any

from trialdiff.http import build_url, get_json


class ClinicalTrialsOfficialClient:
    def __init__(self, base_url: str = "https://clinicaltrials.gov/api/v2") -> None:
        self.base_url = base_url.rstrip("/")

    def study_url(self, nct_id: str) -> str:
        return f"{self.base_url}/studies/{nct_id}"

    def fetch_study(self, nct_id: str) -> tuple[dict[str, Any], str]:
        url = self.study_url(nct_id)
        return get_json(url), url

    def search_studies(
        self,
        *,
        query_cond: str,
        page_size: int = 100,
        page_token: str | None = None,
        fields: list[str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        url = f"{self.base_url}/studies"
        params: dict[str, Any] = {
            "query.cond": query_cond,
            "pageSize": page_size,
            "pageToken": page_token,
        }
        if fields:
            params["fields"] = ",".join(fields)
        return get_json(url, params), build_url(url, params)
