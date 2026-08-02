from __future__ import annotations

import json
import sqlite3
import unittest

from scripts.analyze_event_class_boundary import compute_boundary_stats


def record(*, has_results: bool) -> dict:
    return {
        "hasResults": has_results,
        "protocolSection": {
            "statusModule": {"overallStatus": "COMPLETED"},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Overall survival"}]},
        },
    }


class BoundaryAnalysisTests(unittest.TestCase):
    def test_inclusive_flag_partitions_clean_and_results_cooccurring(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """
            CREATE TABLE trial_versions (
              nct_id text NOT NULL,
              version integer NOT NULL,
              record_json text,
              PRIMARY KEY (nct_id, version)
            );
            CREATE TABLE trial_patches (
              nct_id text NOT NULL,
              from_version integer NOT NULL,
              to_version integer NOT NULL,
              patch_json text NOT NULL
            );
            """
        )
        before = record(has_results=False)
        clean_after = record(has_results=False)
        clean_after["protocolSection"]["outcomesModule"]["primaryOutcomes"][0]["measure"] = (
            "Progression-free survival"
        )
        confounded_after = record(has_results=True)
        confounded_after["protocolSection"]["outcomesModule"]["primaryOutcomes"][0]["measure"] = (
            "Response rate"
        )
        clean_patch = [
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                "value": "Progression-free survival",
            }
        ]
        confounded_patch = [
            {"op": "replace", "path": "/hasResults", "value": True},
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                "value": "Response rate",
            },
        ]
        for nct_id, after, patch in (
            ("NCT00000001", clean_after, clean_patch),
            ("NCT00000002", confounded_after, confounded_patch),
        ):
            connection.execute(
                "INSERT INTO trial_versions VALUES (?, 1, ?)",
                (nct_id, json.dumps(before)),
            )
            connection.execute(
                "INSERT INTO trial_versions VALUES (?, 2, ?)",
                (nct_id, json.dumps(after)),
            )
            connection.execute(
                "INSERT INTO trial_patches VALUES (?, 1, 2, ?)",
                (nct_id, json.dumps(patch)),
            )
        stats = compute_boundary_stats(connection)
        connection.close()

        self.assertEqual(stats["patches"], 2)
        self.assertEqual(stats["inclusive_primary_after_completion"], 2)
        self.assertEqual(stats["results_cooccurring"], 1)
        self.assertEqual(stats["clean"], 1)


if __name__ == "__main__":
    unittest.main()
