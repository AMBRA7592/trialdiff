from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Iterable

from trialdiff.constants import PatchKind, Source
from trialdiff.db import TrialDiffStore
from trialdiff.fetchers.internal import ClinicalTrialsInternalHistoryClient
from trialdiff.fetchers.official import ClinicalTrialsOfficialClient
from trialdiff.jsonpatch import generate_patch
from trialdiff.provenance import Provenance


@dataclass(frozen=True)
class IngestResult:
    nct_id: str
    official_snapshot_stored: bool
    internal_history_stored: bool
    patch_count: int
    error: str | None = None


def ingest_nct_ids(
    *,
    nct_ids: Iterable[str],
    store: TrialDiffStore,
    official_client: ClinicalTrialsOfficialClient | None = None,
    internal_client: ClinicalTrialsInternalHistoryClient | None = None,
    fetch_internal: bool = True,
    corpus_label: str | None = None,
    delay_seconds: float = 0.0,
) -> list[IngestResult]:
    official_client = official_client or ClinicalTrialsOfficialClient()
    internal_client = internal_client or ClinicalTrialsInternalHistoryClient()
    ids = list(nct_ids)
    run_id = store.create_ingest_run(
        corpus_label=corpus_label,
        query={"nct_ids": ids},
        relaxation={},
    )
    results: list[IngestResult] = []
    status = "completed"
    try:
        for nct_id in ids:
            result = ingest_one_nct_id(
                nct_id=nct_id,
                store=store,
                official_client=official_client,
                internal_client=internal_client,
                fetch_internal=fetch_internal,
            )
            if result.error:
                status = "completed_with_errors"
            results.append(result)
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        store.complete_ingest_run(run_id, status=status)
    except Exception as exc:
        store.complete_ingest_run(run_id, status="failed", notes=str(exc))
        raise
    return results


def ingest_one_nct_id(
    *,
    nct_id: str,
    store: TrialDiffStore,
    official_client: ClinicalTrialsOfficialClient,
    internal_client: ClinicalTrialsInternalHistoryClient,
    fetch_internal: bool,
) -> IngestResult:
    try:
        official_record, official_url = official_client.fetch_study(nct_id)
        official_provenance = Provenance.from_payload(
            source=Source.OFFICIAL_V2,
            source_url=official_url,
            payload=official_record,
        )
        stored_nct_id = store.upsert_trial(official_record, official_provenance)
        store.insert_snapshot(stored_nct_id, official_record, official_provenance)
    except Exception as exc:
        return IngestResult(
            nct_id=nct_id,
            official_snapshot_stored=False,
            internal_history_stored=False,
            patch_count=0,
            error=f"official fetch failed: {exc}",
        )

    if not fetch_internal:
        return IngestResult(stored_nct_id, True, False, 0)

    try:
        history_payload, history_url = internal_client.fetch_history_summary(stored_nct_id)
        history_provenance = Provenance.from_payload(
            source=Source.CTGOV_INTERNAL_HISTORY,
            source_url=history_url,
            payload=history_payload,
        )
        changes = ((history_payload.get("history") or {}).get("changes") or [])
        for change in changes:
            store.upsert_version(stored_nct_id, change, history_provenance)
        patch_count = fetch_and_store_adjacent_patches(
            nct_id=stored_nct_id,
            changes=changes,
            store=store,
            internal_client=internal_client,
        )
        return IngestResult(stored_nct_id, True, True, patch_count)
    except Exception as exc:
        return IngestResult(
            nct_id=stored_nct_id,
            official_snapshot_stored=True,
            internal_history_stored=False,
            patch_count=0,
            error=f"internal history fetch failed: {exc}",
        )


def fetch_and_store_adjacent_patches(
    *,
    nct_id: str,
    changes: list[dict[str, Any]],
    store: TrialDiffStore,
    internal_client: ClinicalTrialsInternalHistoryClient,
) -> int:
    patch_count = 0
    versions = sorted(int(change["version"]) for change in changes if "version" in change)
    change_by_version = {int(change["version"]): change for change in changes if "version" in change}
    for from_version, to_version in zip(versions, versions[1:], strict=False):
        payload, url = internal_client.fetch_version(nct_id, from_version, patch_to_version=to_version)
        patch = payload.get("patch") or []
        if payload.get("study"):
            store.update_version_record(nct_id=nct_id, version=from_version, record=payload["study"])
        if not patch:
            continue
        provenance = Provenance.from_payload(
            source=Source.CTGOV_INTERNAL_HISTORY,
            source_url=url,
            payload=payload,
            source_version=str(payload.get("patchVersion") or to_version),
        )
        changed_modules = change_by_version.get(to_version, {}).get("moduleLabels") or []
        store.insert_patch(
            nct_id=nct_id,
            from_version=from_version,
            to_version=to_version,
            patch_kind=PatchKind.CTGOV_HISTORY_PATCH.value,
            patch=patch,
            changed_modules=changed_modules,
            provenance=provenance,
        )
        patch_count += 1
    return patch_count


def build_self_snapshot_patch(old_record: dict[str, Any], new_record: dict[str, Any]) -> list[dict[str, Any]]:
    return generate_patch(old_record, new_record)
