from __future__ import annotations

import tempfile
import unittest

from trialdiff.corpus import locally_matches, select_breast_cancer_corpus, write_corpus


def study(nct_id: str, *, study_type: str = "INTERVENTIONAL", phases: list[str] | None = None, updated: str = "2025-01-01"):
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": f"Trial {nct_id}"},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Sponsor"}},
            "statusModule": {"overallStatus": "RECRUITING", "lastUpdatePostDateStruct": {"date": updated}},
            "designModule": {"studyType": study_type, "phases": phases or ["PHASE2"]},
        }
    }


class FakeOfficialSearchClient:
    def search_studies(self, *, query_cond, page_size=100, page_token=None, fields=None):
        return {
            "studies": [
                study("NCT00000001", phases=["PHASE2"]),
                study("NCT00000002", phases=["PHASE1"]),
                study("NCT00000003", study_type="OBSERVATIONAL", phases=[]),
                study("NCT00000004", phases=["PHASE3"], updated="2020-01-01"),
                study("NCT00000005", phases=["PHASE3"]),
            ]
        }, "https://example.test/api/v2/studies"


class FakeInternalHistoryClient:
    def fetch_history_summary(self, nct_id):
        version_counts = {"NCT00000001": 3, "NCT00000005": 2}
        return {
            "history": {"changes": [{"version": index} for index in range(version_counts[nct_id])]},
            "study": {},
        }, f"https://example.test/api/int/studies/{nct_id}?history=true"


class CorpusTests(unittest.TestCase):
    def test_local_corpus_filters(self) -> None:
        self.assertTrue(locally_matches(study("NCT1", phases=["PHASE2"]), cutoff_date="2021-05-20", allowed_phases={"PHASE2", "PHASE3"}))
        self.assertFalse(locally_matches(study("NCT2", phases=["PHASE1"]), cutoff_date="2021-05-20", allowed_phases={"PHASE2", "PHASE3"}))
        self.assertFalse(locally_matches(study("NCT3", study_type="OBSERVATIONAL"), cutoff_date="2021-05-20", allowed_phases={"PHASE2", "PHASE3"}))
        self.assertFalse(locally_matches(study("NCT4", updated="2020-01-01"), cutoff_date="2021-05-20", allowed_phases={"PHASE2", "PHASE3"}))

    def test_select_corpus_filters_by_history_count(self) -> None:
        selection = select_breast_cancer_corpus(
            official_client=FakeOfficialSearchClient(),
            internal_client=FakeInternalHistoryClient(),
            limit=10,
            delay_seconds=0,
        )

        self.assertEqual(selection.candidate_count, 5)
        self.assertEqual(selection.locally_eligible_count, 2)
        self.assertEqual([study.nct_id for study in selection.selected], ["NCT00000001"])

    def test_write_corpus_outputs_json_and_txt(self) -> None:
        selection = select_breast_cancer_corpus(
            official_client=FakeOfficialSearchClient(),
            internal_client=FakeInternalHistoryClient(),
            limit=10,
            delay_seconds=0,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path, txt_path = write_corpus(selection, tmpdir, "fixture")

            self.assertTrue(json_path.exists())
            self.assertTrue(txt_path.exists())
            self.assertEqual(txt_path.read_text(encoding="utf-8").strip(), "NCT00000001")


if __name__ == "__main__":
    unittest.main()
