from __future__ import annotations

import json
from pathlib import Path
import unittest

from trialdiff.jsonpatch import MISSING, apply_patch, build_value_contexts, generate_patch, resolve_pointer


FIXTURES = Path(__file__).parent / "fixtures"


class JsonPatchTests(unittest.TestCase):
    def load_fixture(self, name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_apply_patch_reconstructs_next_version(self) -> None:
        from_study = self.load_fixture("from_study.json")
        patch = self.load_fixture("patch_to_next.json")
        next_study = apply_patch(from_study, patch)

        self.assertEqual(
            resolve_pointer(next_study, "/protocolSection/outcomesModule/primaryOutcomes/0/measure"),
            "Progression-free survival",
        )
        self.assertEqual(len(resolve_pointer(next_study, "/protocolSection/outcomesModule/primaryOutcomes")), 1)
        self.assertEqual(resolve_pointer(next_study, "/protocolSection/designModule/enrollmentInfo/count"), 80)

    def test_value_contexts_capture_old_and_new_values_sequentially(self) -> None:
        from_study = self.load_fixture("from_study.json")
        patch = self.load_fixture("patch_to_next.json")
        contexts = build_value_contexts(from_study, patch)

        self.assertEqual(contexts[0].old_value, "Overall survival")
        self.assertEqual(contexts[0].new_value, "Progression-free survival")
        self.assertEqual(contexts[1].old_value["measure"], "Hospitalization")
        self.assertIs(contexts[1].new_value, MISSING)
        self.assertEqual(contexts[2].old_value, 120)
        self.assertEqual(contexts[2].new_value, 80)

    def test_generate_patch_handles_simple_snapshot_diff(self) -> None:
        old = {"a": 1, "b": {"c": 2}, "d": [1, 2]}
        new = {"a": 1, "b": {"c": 3}, "d": [1, 2], "e": "new"}
        patch = generate_patch(old, new)

        self.assertIn({"op": "replace", "path": "/b/c", "value": 3}, patch)
        self.assertIn({"op": "add", "path": "/e", "value": "new"}, patch)
        self.assertEqual(apply_patch(old, patch), new)


if __name__ == "__main__":
    unittest.main()
