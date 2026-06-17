from __future__ import annotations

from typing import Any

from trialdiff.http import build_url, get_json


class ClinicalTrialsInternalHistoryClient:
    def __init__(self, base_url: str = "https://clinicaltrials.gov/api/int") -> None:
        self.base_url = base_url.rstrip("/")

    def history_url(self, nct_id: str) -> str:
        return build_url(f"{self.base_url}/studies/{nct_id}", {"history": "true"})

    def fetch_history_summary(self, nct_id: str) -> tuple[dict[str, Any], str]:
        url = f"{self.base_url}/studies/{nct_id}"
        params = {"history": "true"}
        return get_json(url, params), build_url(url, params)

    def version_url(self, nct_id: str, version: int, patch_to_version: int | None = None) -> str:
        url = f"{self.base_url}/studies/{nct_id}/history/{version}"
        return build_url(url, {"patchToVersion": patch_to_version})

    def fetch_version(
        self,
        nct_id: str,
        version: int,
        patch_to_version: int | None = None,
    ) -> tuple[dict[str, Any], str]:
        url = f"{self.base_url}/studies/{nct_id}/history/{version}"
        params = {"patchToVersion": patch_to_version}
        return get_json(url, params), build_url(url, params)
