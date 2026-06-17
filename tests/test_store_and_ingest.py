from __future__ import annotations

import sqlite3
import tempfile
import unittest

from trialdiff.constants import Source
from trialdiff.db import TrialDiffStore, connect, init_db
from trialdiff.ingest import ingest_nct_ids
from trialdiff.provenance import Provenance


def minimal_record(nct_id: str = "NCT00000001") -> dict:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": "Fixture Trial"},
            "statusModule": {
                "overallStatus": "RECRUITING",
                "studyFirstSubmitDate": "2026-01-01",
                "lastUpdatePostDateStruct": {"date": "2026-01-02"},
            },
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Fixture Sponsor", "class": "INDUSTRY"}},
            "conditionsModule": {"conditions": ["Breast Cancer"]},
            "armsInterventionsModule": {"interventions": []},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE2"]},
        },
        "hasResults": False,
    }


class FakeOfficialClient:
    def fetch_study(self, nct_id: str):
        payload = minimal_record(nct_id)
        return payload, f"https://example.test/api/v2/studies/{nct_id}"


class FakeInternalClient:
    def fetch_history_summary(self, nct_id: str):
        payload = {
            "study": minimal_record(nct_id),
            "history": {
                "changes": [
                    {"version": 0, "date": "2026-01-01", "status": "NOT_YET_RECRUITING", "studyType": "INTERVENTIONAL"},
                    {
                        "version": 1,
                        "date": "2026-02-01",
                        "status": "RECRUITING",
                        "studyType": "INTERVENTIONAL",
                        "moduleLabels": ["Outcome Measures"],
                    },
                ]
            },
        }
        return payload, f"https://example.test/api/int/studies/{nct_id}?history=true"

    def fetch_version(self, nct_id: str, version: int, patch_to_version: int | None = None):
        payload = {
            "studyVersion": version,
            "patchVersion": patch_to_version,
            "study": minimal_record(nct_id),
            "patch": [
                {
                    "op": "replace",
                    "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                    "value": "Progression-free survival",
                }
            ],
        }
        return payload, f"https://example.test/api/int/studies/{nct_id}/history/{version}?patchToVersion={patch_to_version}"


class StoreAndIngestTests(unittest.TestCase):
    def test_trial_snapshot_and_patch_writes_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/trialdiff.sqlite3"
            init_db(db_path)
            connection = connect(db_path)
            try:
                store = TrialDiffStore(connection)
                record = minimal_record()
                provenance = Provenance.from_payload(
                    source=Source.OFFICIAL_V2,
                    source_url="https://example.test/study",
                    payload=record,
                )
                nct_id = store.upsert_trial(record, provenance)
                store.insert_snapshot(nct_id, record, provenance)
                store.insert_snapshot(nct_id, record, provenance)
                store.insert_patch(
                    nct_id=nct_id,
                    from_version=0,
                    to_version=1,
                    patch_kind="ctgov_history_patch",
                    patch=[{"op": "replace", "path": "/x", "value": 1}],
                    changed_modules=["Outcome Measures"],
                    provenance=provenance,
                )
                store.insert_patch(
                    nct_id=nct_id,
                    from_version=0,
                    to_version=1,
                    patch_kind="ctgov_history_patch",
                    patch=[{"op": "replace", "path": "/x", "value": 1}],
                    changed_modules=["Outcome Measures"],
                    provenance=provenance,
                )
                connection.commit()

                snapshot_count = connection.execute("SELECT COUNT(*) FROM trial_snapshots").fetchone()[0]
                patch_count = connection.execute("SELECT COUNT(*) FROM trial_patches").fetchone()[0]
                self.assertEqual(snapshot_count, 1)
                self.assertEqual(patch_count, 1)
            finally:
                connection.close()

    def test_ingest_uses_official_and_internal_clients(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/trialdiff.sqlite3"
            init_db(db_path)
            connection = connect(db_path)
            try:
                store = TrialDiffStore(connection)
                results = ingest_nct_ids(
                    nct_ids=["NCT00000001"],
                    store=store,
                    official_client=FakeOfficialClient(),
                    internal_client=FakeInternalClient(),
                    fetch_internal=True,
                    corpus_label="fixture",
                    delay_seconds=0,
                )
                connection.commit()

                self.assertIsNone(results[0].error)
                self.assertEqual(results[0].patch_count, 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM trials").fetchone()[0], 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM trial_versions").fetchone()[0], 2)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM trial_patches").fetchone()[0], 1)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
