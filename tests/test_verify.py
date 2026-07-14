from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from trialdiff.verify import verify_record_file


REPO_ROOT = Path(__file__).resolve().parent.parent
ALPHA_RECORD = REPO_ROOT / "records" / "evt_NCT01441947_v5_v6_da10803d7578.json"
EVENT_CLASS_RECORD = (
    REPO_ROOT
    / "event_class_records_v0.1.1"
    / "records"
    / "evt_NCT04278144_v33_v34_bdd9f29ed71e.json"
)


@unittest.skipUnless(ALPHA_RECORD.exists(), "frozen alpha package not present")
class VerifyAlphaRecordTests(unittest.TestCase):
    def test_frozen_alpha_record_verifies(self) -> None:
        result = verify_record_file(ALPHA_RECORD)
        self.assertEqual(result.schema, "trialdiff.alpha_demo_record")
        self.assertTrue(result.ok, result.checks)

    def test_tampered_alpha_record_fails(self) -> None:
        record = json.loads(ALPHA_RECORD.read_text(encoding="utf-8"))
        record["canonical_evidence_record"]["classification"]["severity"] = "low"
        with tempfile.TemporaryDirectory() as tempdir:
            tampered = Path(tempdir) / ALPHA_RECORD.name
            tampered.write_text(json.dumps(record), encoding="utf-8")
            result = verify_record_file(tampered)
        self.assertFalse(result.ok)
        failed = {name for name, passed, _ in result.checks if not passed}
        self.assertIn("evidence_canonical_hash", failed)


@unittest.skipUnless(EVENT_CLASS_RECORD.exists(), "event-class package not present")
class VerifyEventClassRecordTests(unittest.TestCase):
    def test_frozen_event_class_record_verifies(self) -> None:
        result = verify_record_file(EVENT_CLASS_RECORD)
        self.assertEqual(result.schema, "trialdiff.evidence_record")
        self.assertTrue(result.ok, result.checks)

    def test_reserialized_record_fails_canonical_bytes(self) -> None:
        record = json.loads(EVENT_CLASS_RECORD.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tempdir:
            tampered = Path(tempdir) / EVENT_CLASS_RECORD.name
            tampered.write_text(json.dumps(record, indent=2), encoding="utf-8")
            result = verify_record_file(tampered)
        failed = {name for name, passed, _ in result.checks if not passed}
        self.assertIn("canonical_bytes", failed)

    def test_edited_classification_fails_event_id(self) -> None:
        record = json.loads(EVENT_CLASS_RECORD.read_text(encoding="utf-8"))
        record["classification"]["event_classes"] = ["outcome_edit_cooccurs_with_results_posting"]
        with tempfile.TemporaryDirectory() as tempdir:
            tampered = Path(tempdir) / EVENT_CLASS_RECORD.name
            tampered.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            result = verify_record_file(tampered)
        failed = {name for name, passed, _ in result.checks if not passed}
        self.assertIn("event_id", failed)

    def test_unknown_schema_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "evt_unknown.json"
            path.write_text(json.dumps({"schema": "something.else"}), encoding="utf-8")
            result = verify_record_file(path)
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
