from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from trialdiff.classifier.materiality import (
    ClassifierRule,
    classify_patch,
    provenance_for_event,
    rule_set_hash,
    rule_table_hash,
)
from trialdiff.db import connect, init_db
from trialdiff.event_classes import EVENT_CLASS_RULE_SET_HASH, combined_rule_set_hash
from trialdiff.ruleset import implementation_source_hash


# Golden hashes pin the active rule semantics. If one of these assertions
# fails, the rule set changed: bump the relevant version string, record the
# old->new hash transition in ERRATA.md, and only then update the constant.
GOLDEN_EVENT_CLASS_RULE_SET_HASH = "91892060d8cd852c68a8afc0806cba298701702417025433cf001779bee82350"
GOLDEN_TRIAGE_RULE_TABLE_HASH = "6fc6d7533e740cc38ca0ba0425927ade66f2f90b067963c5cf52d08a88f8d883"
GOLDEN_TRIAGE_RULE_SET_HASH = "af5e5835e00a5fcfe2a17fd02b5fc244c2564104f93f78a1d77d7889f12a178b"
GOLDEN_COMBINED_RULE_SET_HASH = "95326e30a51f979e331037a0e0564f086ff568795d7659d158b0c66a31129b1b"

# Historical hashes carried by the frozen packages; they must never be
# reused for new generations after a definition change.
FROZEN_V011_EVENT_CLASS_RULE_SET_HASH = "a6734d37c1adc34c5c3b770ec40fbedcf8e8e2fa4bc9d56d4eab55d2e5867c4e"
FROZEN_V012_EVENT_CLASS_RULE_SET_HASH = "07957f8b90549d4f42387f51b471ecde9901b6db63bbc27b84c73631603407c0"


def load_active_rules(connection) -> list[ClassifierRule]:
    # Load through the same store method production uses (cli.py classify),
    # so the golden hash covers the real rule pipeline.
    from trialdiff.db import TrialDiffStore

    return [ClassifierRule.from_row(row) for row in TrialDiffStore(connection).load_active_rules()]


class GoldenHashTests(unittest.TestCase):
    def test_implementation_source_hash_changes_with_executable_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            source = Path(tempdir) / "predicate.py"
            source.write_text("def predicate():\n    return True\n", encoding="utf-8")
            first = implementation_source_hash({"predicate": source})
            source.write_text("def predicate():\n    return False\n", encoding="utf-8")
            second = implementation_source_hash({"predicate": source})
        self.assertNotEqual(first, second)

    def test_event_class_rule_set_hash_is_pinned(self) -> None:
        self.assertEqual(EVENT_CLASS_RULE_SET_HASH, GOLDEN_EVENT_CLASS_RULE_SET_HASH)

    def test_event_class_hash_differs_from_frozen_v011_hash(self) -> None:
        # The 2026-07 whyStopped definition tightening must yield a new hash;
        # regenerated records must not masquerade as the frozen generation.
        self.assertNotEqual(EVENT_CLASS_RULE_SET_HASH, FROZEN_V011_EVENT_CLASS_RULE_SET_HASH)

    def test_event_class_hash_differs_from_frozen_v012_hash(self) -> None:
        # E4 changed executable semantics while the high-level class names
        # remained stable. Implementation-source pinning must rotate the hash.
        self.assertNotEqual(EVENT_CLASS_RULE_SET_HASH, FROZEN_V012_EVENT_CLASS_RULE_SET_HASH)

    def test_module_pin_matches_golden_triage_hash(self) -> None:
        from trialdiff.classifier.materiality import (
            V021_TRIAGE_RULE_SET_HASH,
            V021_TRIAGE_RULE_TABLE_HASH,
        )

        self.assertEqual(V021_TRIAGE_RULE_TABLE_HASH, GOLDEN_TRIAGE_RULE_TABLE_HASH)
        self.assertEqual(V021_TRIAGE_RULE_SET_HASH, GOLDEN_TRIAGE_RULE_SET_HASH)

    def test_fresh_database_reproduces_pinned_triage_rule_set_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = os.path.join(tempdir, "golden.sqlite3")
            init_db(db_path)
            connection = connect(db_path)
            try:
                active_rules = load_active_rules(connection)
                table_hash = rule_table_hash(active_rules)
                triage_hash = rule_set_hash(active_rules)
            finally:
                connection.close()
        self.assertEqual(table_hash, GOLDEN_TRIAGE_RULE_TABLE_HASH)
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


# Classifies a patch whose two matched rules carry categories with EQUAL
# priority (both outside the priority table), the shape that exposed
# set-iteration-order nondeterminism, and prints the event hash.
HASHSEED_PROBE = """
from trialdiff.classifier.materiality import ClassifierRule, classify_patch, provenance_for_event

rules = [
    ClassifierRule(
        rule_key="probe_reconciliation",
        path_pattern="/protocolSection/statusModule/statusVerifiedDate",
        op_filter=[],
        value_filter={},
        severity="low",
        category="results_reconciliation",
        timing_sensitive=False,
        description="probe",
    ),
    ClassifierRule(
        rule_key="probe_contact",
        path_pattern="/protocolSection/statusModule/statusVerifiedDate",
        op_filter=[],
        value_filter={},
        severity="low",
        category="administrative_contact_change",
        timing_sensitive=False,
        description="probe",
    ),
]
from_record = {"protocolSection": {"statusModule": {"statusVerifiedDate": "2025-01"}}}
patch = [{"op": "replace", "path": "/protocolSection/statusModule/statusVerifiedDate", "value": "2025-02"}]
event = classify_patch(
    nct_id="NCT00000002",
    from_version=1,
    to_version=2,
    from_record=from_record,
    patch=patch,
    rules=rules,
    submitted_date="2026-01-01",
)
assert event is not None
assert len(event.categories) >= 2, event.categories
print(provenance_for_event(event).raw_hash)
"""


class CrossProcessDeterminismTests(unittest.TestCase):
    def probe_hash(self, hashseed: str) -> str:
        env = os.environ.get
        result = subprocess.run(
            [sys.executable, "-c", HASHSEED_PROBE],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent,
            env={"PATH": env("PATH", ""), "PYTHONHASHSEED": hashseed},
            check=True,
        )
        return result.stdout.strip()

    def test_event_hash_is_stable_across_hash_seeds(self) -> None:
        # Regression test for the PYTHONHASHSEED-dependent category
        # tie-ordering found in the pre-merge audit: the same inputs must
        # hash identically in fresh interpreters with different seeds.
        hashes = {self.probe_hash(seed) for seed in ("0", "1", "4242")}
        self.assertEqual(len(hashes), 1, hashes)

    def test_postgres_export_is_stable_across_hash_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = Path(tempdir) / "export.sqlite3"
            init_db(db_path)
            outputs = []
            for hashseed in ("0", "1", "4242"):
                result = subprocess.run(
                    [
                        sys.executable,
                        "scripts/sqlite_to_postgres.py",
                        str(db_path),
                        "--truncate",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).resolve().parent.parent,
                    env={
                        "PATH": os.environ.get("PATH", ""),
                        "PYTHONHASHSEED": hashseed,
                    },
                    check=True,
                )
                outputs.append(result.stdout)
        self.assertEqual(len(set(outputs)), 1)


class VolatileKeySweepTests(unittest.TestCase):
    VOLATILE_KEYS = {"created_at", "generated_at", "fetched_at"}

    def walk_keys(self, value) -> set[str]:
        keys: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                keys.add(key)
                keys |= self.walk_keys(item)
        elif isinstance(value, list):
            for item in value:
                keys |= self.walk_keys(item)
        return keys

    def test_hashed_payloads_contain_no_wall_clock_keys(self) -> None:
        # The E2 invariant, enforced as a sweep instead of per-artifact
        # memory: content hashed into raw_hash / canonical_hash must never
        # contain wall-clock fields.
        from trialdiff.classifier.materiality import ClassifierRule, classify_patch
        from trialdiff.evidence import build_evidence_record

        rules = [
            ClassifierRule(
                rule_key="probe",
                path_pattern="/protocolSection/outcomesModule/primaryOutcomes/*/measure",
                op_filter=[],
                value_filter={},
                severity="critical",
                category="primary_outcome_change",
                timing_sensitive=False,
                description="probe",
            )
        ]
        from_record = {
            "protocolSection": {
                "statusModule": {"overallStatus": "COMPLETED"},
                "outcomesModule": {"primaryOutcomes": [{"measure": "OS"}]},
            }
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                "value": "PFS",
            }
        ]
        event = classify_patch(
            nct_id="NCT00000003",
            from_version=1,
            to_version=2,
            from_record=from_record,
            patch=patch,
            rules=rules,
            submitted_date="2026-01-01",
        )
        assert event is not None
        self.assertFalse(self.walk_keys(event.content_dict()) & self.VOLATILE_KEYS)

        row = {
            "nct_id": "NCT00000003",
            "from_version": 1,
            "to_version": 2,
            "submitted_date": "2026-01-01",
            "timing_context": "post_recruitment",
            "severity_pre_timing": "critical",
            "severity": "critical",
            "category": "primary_outcome_change",
            "categories_json": '["primary_outcome_change"]',
            "changed_paths_json": '["/protocolSection/outcomesModule/primaryOutcomes/0/measure"]',
            "deterministic_rules_json": '["probe"]',
            "value_signals_json": "[]",
            "event_classes_json": '["primary_endpoint_changed_after_primary_completion_without_results_reconciliation"]',
            "needs_human_review": 1,
            "rule_set_hash": "0" * 64,
            "patch_json": json.dumps(patch),
            "patch_hash": "1" * 64,
            "patch_source": "ctgov_internal_history",
            "patch_source_url": "",
            "patch_raw_hash": "",
            "from_snapshot_hash": None,
            "to_snapshot_hash": None,
            "materiality_event_hash": "",
        }
        record = build_evidence_record(row)
        self.assertFalse(self.walk_keys(record["canonical"]) & self.VOLATILE_KEYS)


if __name__ == "__main__":
    unittest.main()
