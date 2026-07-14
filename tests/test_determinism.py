from __future__ import annotations

import dataclasses
import os
import tempfile
import unittest

from trialdiff.classifier.materiality import (
    ClassifierRule,
    classify_patch,
    provenance_for_event,
    rule_set_hash,
)
from trialdiff.db import connect, init_db
from trialdiff.event_classes import EVENT_CLASS_RULE_SET_HASH, combined_rule_set_hash


# Golden hashes pin the active rule semantics. If one of these assertions
# fails, the rule set changed: bump the relevant version string, record the
# old->new hash transition in ERRATA.md, and only then update the constant.
GOLDEN_EVENT_CLASS_RULE_SET_HASH = "20c8e4833ddcaf8280f7bfdbcbffebb68e6eb4fde9c9d02d0a1fa3415c7a894e"
GOLDEN_TRIAGE_RULE_SET_HASH = "6fc6d7533e740cc38ca0ba0425927ade66f2f90b067963c5cf52d08a88f8d883"
GOLDEN_COMBINED_RULE_SET_HASH = "ff5b5dcc8df8e2fd3206405a557a67f6cd1b3a22d2f2069666ec2357d783d0e4"

# Historical hashes carried by the frozen packages; they must never be
# reused for new generations after a definition change.
FROZEN_V011_EVENT_CLASS_RULE_SET_HASH = "a6734d37c1adc34c5c3b770ec40fbedcf8e8e2fa4bc9d56d4eab55d2e5867c4e"


def load_active_rules(connection) -> list[ClassifierRule]:
    rows = connection.execute("SELECT * FROM classifier_rules WHERE active=1").fetchall()
    return [ClassifierRule.from_row(row) for row in rows]


class GoldenHashTests(unittest.TestCase):
    def test_event_class_rule_set_hash_is_pinned(self) -> None:
        self.assertEqual(EVENT_CLASS_RULE_SET_HASH, GOLDEN_EVENT_CLASS_RULE_SET_HASH)

    def test_event_class_hash_differs_from_frozen_v011_hash(self) -> None:
        # The 2026-07 whyStopped definition tightening must yield a new hash;
        # regenerated records must not masquerade as the frozen generation.
        self.assertNotEqual(EVENT_CLASS_RULE_SET_HASH, FROZEN_V011_EVENT_CLASS_RULE_SET_HASH)

    def test_fresh_database_reproduces_pinned_triage_rule_set_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = os.path.join(tempdir, "golden.sqlite3")
            init_db(db_path)
            connection = connect(db_path)
            try:
                triage_hash = rule_set_hash(load_active_rules(connection))
            finally:
                connection.close()
        self.assertEqual(triage_hash, GOLDEN_TRIAGE_RULE_SET_HASH)
        self.assertEqual(
            combined_rule_set_hash(triage_rule_set_hash=triage_hash),
            GOLDEN_COMBINED_RULE_SET_HASH,
        )


class ReplayDeterminismTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tempdir.name, "replay.sqlite3")
        init_db(db_path)
        self.connection = connect(db_path)
        self.rules = load_active_rules(self.connection)

    def tearDown(self) -> None:
        self.connection.close()
        self.tempdir.cleanup()

    def classify_once(self):
        from_record = {
            "protocolSection": {
                "statusModule": {
                    "overallStatus": "TERMINATED",
                    "whyStopped": "Recruitment failed",
                },
                "outcomesModule": {"primaryOutcomes": [{"measure": "Overall survival"}]},
                "designModule": {},
            }
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                "value": "Progression-free survival",
            }
        ]
        event = classify_patch(
            nct_id="NCT00000001",
            from_version=1,
            to_version=2,
            from_record=from_record,
            patch=patch,
            rules=self.rules,
            submitted_date="2026-01-01",
        )
        self.assertIsNotNone(event)
        return event

    def test_replay_reproduces_identical_event_hash(self) -> None:
        first = self.classify_once()
        second = self.classify_once()
        # Force distinct wall-clock stamps to prove created_at cannot leak
        # into the hashed content.
        second = dataclasses.replace(second, created_at="1999-01-01T00:00:00Z")
        self.assertNotEqual(first.created_at, second.created_at)
        self.assertEqual(first.content_dict(), second.content_dict())
        self.assertEqual(
            provenance_for_event(first).raw_hash,
            provenance_for_event(second).raw_hash,
        )
        self.assertEqual(
            provenance_for_event(first).source_version,
            provenance_for_event(second).source_version,
        )

    def test_created_at_still_present_in_storage_dict(self) -> None:
        event = self.classify_once()
        self.assertIn("created_at", event.as_dict())
        self.assertNotIn("created_at", event.content_dict())


if __name__ == "__main__":
    unittest.main()
