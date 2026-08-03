from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest

from scripts.seed_from_records import seed_evidence_record_file
from scripts.sqlite_to_postgres import build_export, generation_metadata
from trialdiff.db import connect, init_db


REPO_ROOT = Path(__file__).resolve().parent.parent
FROZEN_RECORD = sorted((REPO_ROOT / "event_class_records_v0.1.2" / "records").glob("evt_*.json"))[0]


class PostgresGenerationExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "source.sqlite3"
        init_db(self.db_path)
        raw_text = FROZEN_RECORD.read_text(encoding="utf-8")
        connection = connect(self.db_path)
        try:
            seed_evidence_record_file(connection, json.loads(raw_text), raw_text, Counter())
            connection.commit()
        finally:
            connection.close()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_full_replace_targets_store_and_activates_explicit_generation(self) -> None:
        sql = build_export(
            self.db_path,
            package_generation="v0.1.2",
            truncate=True,
            evidence_only=False,
            supersedes=None,
            activate_generation=True,
            batch_size=100,
        )

        self.assertIn("TRUNCATE evidence_record_supersessions, evidence_record_store", sql)
        self.assertIn("INSERT INTO evidence_record_generations", sql)
        self.assertIn("INSERT INTO evidence_record_store", sql)
        self.assertIn("generation metadata mismatch", sql)
        self.assertIn("source corpus metadata does not match target corpus", sql)
        self.assertNotIn("INSERT INTO evidence_records", sql)
        self.assertIn("SELECT trialdiff_activate_evidence_generation('v0.1.2');", sql)

    def test_additive_export_contains_only_generation_rows_and_complete_mapping_gate(self) -> None:
        sql = build_export(
            self.db_path,
            package_generation="v0.1.3",
            truncate=False,
            evidence_only=True,
            supersedes="v0.1.2",
            activate_generation=False,
            batch_size=100,
        )

        self.assertNotIn("TRUNCATE", sql)
        self.assertNotIn("INSERT INTO trials", sql)
        self.assertNotIn("SELECT setval", sql)
        self.assertIn("INSERT INTO evidence_record_store", sql)
        self.assertIn("supersession requires a complete one-to-one transition map", sql)
        self.assertIn("INSERT INTO evidence_record_supersessions", sql)
        self.assertNotIn("trialdiff_activate_evidence_generation('v0.1.3')", sql)

    def test_additive_export_cannot_activate_in_same_transaction(self) -> None:
        with self.assertRaisesRegex(ValueError, "verified before separate activation"):
            build_export(
                self.db_path,
                package_generation="v0.1.3",
                truncate=False,
                evidence_only=True,
                supersedes="v0.1.2",
                activate_generation=True,
                batch_size=100,
            )

    def test_generation_labels_are_semver_scoped(self) -> None:
        with self.assertRaisesRegex(ValueError, "vMAJOR.MINOR.PATCH"):
            build_export(
                self.db_path,
                package_generation="current",
                truncate=True,
                evidence_only=False,
                supersedes=None,
                activate_generation=False,
                batch_size=100,
            )

    def test_generation_metadata_is_package_scoped(self) -> None:
        connection = connect(self.db_path)
        try:
            expected_memberships = sum(
                len(json.loads(row[0]))
                for row in connection.execute("SELECT event_classes_json FROM evidence_records")
            )
            metadata = generation_metadata(connection, self.db_path)
        finally:
            connection.close()

        self.assertEqual(metadata["record_count"], 1)
        self.assertEqual(metadata["represented_trial_count"], 1)
        self.assertEqual(metadata["membership_count"], expected_memberships)
        self.assertEqual(len(metadata["rule_set_hash"]), 64)
        self.assertEqual(len(metadata["source_database_sha256"]), 64)

    def test_generation_metadata_rejects_invalid_rule_hash(self) -> None:
        connection = connect(self.db_path)
        try:
            connection.execute("UPDATE evidence_records SET rule_set_hash = 'not-a-published-hash'")
            connection.commit()
            with self.assertRaisesRegex(ValueError, "exactly one nonempty 64-character"):
                generation_metadata(connection, self.db_path)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
