from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest

from trialdiff.db import TrialDiffStore, connect, init_db
from trialdiff.evidence import (
    EVIDENCE_VERSION,
    build_event_id,
    generate_evidence_records,
)
from trialdiff.provenance import canonical_json, sha256_json, sha256_text


FETCHED_AT = "2026-05-21T12:00:00Z"


def primary_outcome_record(nct_id: str, measure: str, status: str = "COMPLETED") -> dict:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": "Evidence Fixture Trial"},
            "statusModule": {
                "overallStatus": status,
                "studyFirstSubmitDate": "2022-01-01",
                "lastUpdatePostDateStruct": {"date": "2026-01-01"},
            },
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Fixture Sponsor", "class": "INDUSTRY"}},
            "conditionsModule": {"conditions": ["Breast Cancer"]},
            "armsInterventionsModule": {"interventions": []},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE3"]},
            "outcomesModule": {"primaryOutcomes": [{"measure": measure}]},
        },
        "hasResults": False,
    }


def insert_evidence_fixture(
    connection: sqlite3.Connection,
    *,
    nct_id: str = "NCT00000001",
    severity: str = "critical",
    severity_pre_timing: str = "critical",
    category: str = "primary_outcome_change",
    timing_context: str = "post_recruitment",
    rule_set_hash: str = "rulehash-primary",
    changed_paths: list[str] | None = None,
    deterministic_rules: list[str] | None = None,
    value_signals: list[dict] | None = None,
) -> dict[str, str]:
    changed_paths = changed_paths or ["/protocolSection/outcomesModule/primaryOutcomes/0/measure"]
    deterministic_rules = deterministic_rules or ["primary_outcome_any_change"]
    value_signals = value_signals or []
    record_v1 = primary_outcome_record(nct_id, "Overall survival")
    record_v2 = primary_outcome_record(nct_id, "Progression-free survival")
    patch = [{"op": "replace", "path": changed_paths[0], "value": "Progression-free survival"}]
    record_v1_hash = sha256_json(record_v1)
    record_v2_hash = sha256_json(record_v2)
    patch_hash = sha256_json(patch)
    connection.execute(
        """
        INSERT INTO trials (
          nct_id, brief_title, official_title, lead_sponsor, lead_sponsor_class,
          conditions_json, interventions_json, overall_status, phase_json, study_type,
          last_update_posted, first_submitted_date, has_results, current_record_json,
          current_record_hash, source, source_url, fetched_at, source_version, raw_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            nct_id,
            "Evidence Fixture Trial",
            None,
            "Fixture Sponsor",
            "INDUSTRY",
            canonical_json(["Breast Cancer"]),
            canonical_json([]),
            "COMPLETED",
            canonical_json(["PHASE3"]),
            "INTERVENTIONAL",
            "2026-01-01",
            "2022-01-01",
            0,
            canonical_json(record_v2),
            record_v2_hash,
            "official_v2",
            f"https://clinicaltrials.gov/study/{nct_id}",
            FETCHED_AT,
            None,
            record_v2_hash,
        ),
    )
    for version, record, record_hash in ((1, record_v1, record_v1_hash), (2, record_v2, record_v2_hash)):
        connection.execute(
            """
            INSERT INTO trial_versions (
              nct_id, version, submitted_date, overall_status, study_type,
              module_labels_json, review_not_passed, unposted_events_json,
              record_json, record_hash, source, source_url, fetched_at, source_version, raw_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nct_id,
                version,
                f"2026-01-0{version}",
                "COMPLETED",
                "INTERVENTIONAL",
                canonical_json(["Outcome Measures"]),
                0,
                canonical_json([]),
                canonical_json(record),
                record_hash,
                "ctgov_internal_history",
                f"https://clinicaltrials.gov/api/int/studies/{nct_id}/history/{version}",
                FETCHED_AT,
                str(version),
                record_hash,
            ),
        )
    connection.execute(
        """
        INSERT INTO trial_patches (
          nct_id, from_version, to_version, patch_kind, patch_json, patch_hash,
          changed_paths_json, changed_modules_json, op_counts_json, source, source_url,
          fetched_at, source_version, raw_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            nct_id,
            1,
            2,
            "ctgov_history_patch",
            canonical_json(patch),
            patch_hash,
            canonical_json(changed_paths),
            canonical_json(["Outcome Measures"]),
            canonical_json({"replace": 1}),
            "ctgov_internal_history",
            f"https://clinicaltrials.gov/api/int/studies/{nct_id}/history/1?patchToVersion=2",
            FETCHED_AT,
            "1-to-2",
            sha256_json({"patch": patch}),
        ),
    )
    event_payload = {
        "nct_id": nct_id,
        "from_version": 1,
        "to_version": 2,
        "submitted_date": "2026-01-02",
        "timing_context": timing_context,
        "severity_pre_timing": severity_pre_timing,
        "severity": severity,
        "category": category,
        "categories": [category],
        "changed_paths": changed_paths,
        "deterministic_rules": deterministic_rules,
        "value_signals": value_signals,
        "needs_human_review": severity in {"high", "critical"},
        "created_at": FETCHED_AT,
        "rule_set_hash": rule_set_hash,
    }
    connection.execute(
        """
        INSERT INTO materiality_events (
          nct_id, from_version, to_version, submitted_date, timing_context,
          severity_pre_timing, severity, category, categories_json, changed_paths_json,
          deterministic_rules_json, value_signals_json, summary, summary_source,
          needs_human_review, created_at, rule_set_hash, source, source_url, fetched_at,
          source_version, raw_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            nct_id,
            1,
            2,
            "2026-01-02",
            timing_context,
            severity_pre_timing,
            severity,
            category,
            canonical_json([category]),
            canonical_json(changed_paths),
            canonical_json(deterministic_rules),
            canonical_json(value_signals),
            None,
            None,
            1 if severity in {"high", "critical"} else 0,
            FETCHED_AT,
            rule_set_hash,
            "derived_classifier",
            "trialdiff://classifier/materiality",
            FETCHED_AT,
            sha256_json(event_payload),
            sha256_json(event_payload),
        ),
    )
    return {
        "from_snapshot_hash": record_v1_hash,
        "to_snapshot_hash": record_v2_hash,
        "patch_hash": patch_hash,
        "rule_set_hash": rule_set_hash,
    }


class EvidenceRecordTests(unittest.TestCase):
    def test_event_id_is_deterministic_and_path_order_stable(self) -> None:
        first = build_event_id(
            nct_id="NCT00000001",
            from_version=1,
            to_version=2,
            patch_hash="patchhash",
            category="primary_outcome_change",
            changed_paths=["/b", "/a"],
            rule_set_hash="rulehash",
            evidence_version=EVIDENCE_VERSION,
        )
        second = build_event_id(
            nct_id="NCT00000001",
            from_version=1,
            to_version=2,
            patch_hash="patchhash",
            category="primary_outcome_change",
            changed_paths=["/a", "/b"],
            rule_set_hash="rulehash",
            evidence_version=EVIDENCE_VERSION,
        )

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("evt_NCT00000001_v1_v2_"))

    def test_generate_evidence_record_preserves_hashes_claims_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/trialdiff.sqlite3"
            init_db(db_path)
            connection = connect(db_path)
            try:
                hashes = insert_evidence_fixture(connection)
                store = TrialDiffStore(connection)
                result = generate_evidence_records(store)
                connection.commit()

                self.assertEqual(result.generated, 1)
                row = connection.execute("SELECT * FROM evidence_records").fetchone()
                self.assertIsNotNone(row)
                assert row is not None
                canonical = json.loads(row["canonical_json"])
                supported = json.loads(row["claims_supported_json"])
                not_supported = json.loads(row["claims_not_supported_json"])

                self.assertEqual(canonical["schema"], "trialdiff.evidence_record")
                self.assertEqual(canonical["evidence_version"], EVIDENCE_VERSION)
                self.assertEqual(canonical["provenance"]["patch_hash"], hashes["patch_hash"])
                self.assertEqual(canonical["provenance"]["from_snapshot_hash"], hashes["from_snapshot_hash"])
                self.assertEqual(canonical["provenance"]["to_snapshot_hash"], hashes["to_snapshot_hash"])
                self.assertEqual(canonical["classification"]["rule_set_hash"], hashes["rule_set_hash"])
                self.assertEqual(row["canonical_hash"], sha256_text(row["canonical_json"]))
                self.assertTrue(any("primary outcome" in claim for claim in supported))
                self.assertIn("That sponsor intent can be inferred from this registry change.", not_supported)
                self.assertIn("That the change was or was not disclosed in a manuscript.", not_supported)
                self.assertIn("That TrialDiff determines regulatory compliance or non-compliance.", not_supported)
            finally:
                connection.close()

    def test_secondary_outcome_claims_are_neutral_for_post_completion_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/trialdiff.sqlite3"
            init_db(db_path)
            connection = connect(db_path)
            try:
                insert_evidence_fixture(
                    connection,
                    category="secondary_outcome_change",
                    severity="critical",
                    severity_pre_timing="high",
                    changed_paths=["/protocolSection/outcomesModule/secondaryOutcomes/0/measure"],
                    deterministic_rules=["secondary_outcome_any_change"],
                )
                store = TrialDiffStore(connection)
                generate_evidence_records(store)
                connection.commit()

                row = connection.execute("SELECT * FROM evidence_records").fetchone()
                supported = json.loads(row["claims_supported_json"])
                not_supported = json.loads(row["claims_not_supported_json"])
                self.assertTrue(any("secondary outcome" in claim for claim in supported))
                self.assertTrue(any("post_recruitment" in claim for claim in supported))
                self.assertIn("That this post-completion change reflects outcome switching rather than a legitimate registry correction.", not_supported)
                self.assertIn("That the change was or was not disclosed in a manuscript.", not_supported)
            finally:
                connection.close()

    def test_generation_is_idempotent_and_force_rewrites_with_bumped_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/trialdiff.sqlite3"
            init_db(db_path)
            connection = connect(db_path)
            try:
                insert_evidence_fixture(connection)
                store = TrialDiffStore(connection)
                first = generate_evidence_records(store)
                second = generate_evidence_records(store)
                connection.commit()
                first_row = connection.execute("SELECT event_id, evidence_version FROM evidence_records").fetchone()

                self.assertEqual(first.generated, 1)
                self.assertEqual(second.generated, 0)
                self.assertEqual(second.skipped, 1)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM evidence_records").fetchone()[0], 1)

                rewritten = generate_evidence_records(store, force=True, evidence_version=2)
                connection.commit()
                rows = connection.execute("SELECT event_id, evidence_version FROM evidence_records").fetchall()

                self.assertEqual(rewritten.deleted, 1)
                self.assertEqual(rewritten.generated, 1)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["evidence_version"], 2)
                self.assertNotEqual(rows[0]["event_id"], first_row["event_id"])
            finally:
                connection.close()

    def test_low_and_medium_events_are_not_exported_as_evidence_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/trialdiff.sqlite3"
            init_db(db_path)
            connection = connect(db_path)
            try:
                insert_evidence_fixture(
                    connection,
                    severity="medium",
                    severity_pre_timing="medium",
                    category="timeline_shift",
                    changed_paths=["/protocolSection/statusModule/completionDateStruct/date"],
                    deterministic_rules=["timeline_completion_change"],
                )
                store = TrialDiffStore(connection)
                result = generate_evidence_records(store)
                connection.commit()

                self.assertEqual(result.generated, 0)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM evidence_records").fetchone()[0], 0)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
