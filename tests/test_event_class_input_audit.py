from __future__ import annotations

import json
import sqlite3
import unittest

from scripts.audit_event_class_inputs import compute_input_audit


def record(outcomes: list[dict]) -> dict:
    return {
        "protocolSection": {
            "statusModule": {"overallStatus": "COMPLETED"},
            "outcomesModule": {
                "primaryOutcomes": [{"measure": "Overall survival"}],
                "secondaryOutcomes": outcomes,
            },
            "designModule": {},
        },
        "hasResults": False,
    }


class EventClassInputAuditTests(unittest.TestCase):
    def new_connection(self) -> sqlite3.Connection:
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
        return connection

    def test_sequential_disagreement_is_reported_without_pinning_historical_total(self) -> None:
        connection = self.new_connection()
        reappearing = {"measure": "Cohort overall survival"}
        removed = {"measure": "All-patient overall survival"}
        retained = {"measure": "Progression-free survival"}
        added = {"measure": "Duration of response"}
        before = record([retained, reappearing, removed])
        after = record([retained, reappearing, added])
        patch = [
            {"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes/1"},
            {"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes/1"},
            {
                "op": "add",
                "path": "/protocolSection/outcomesModule/secondaryOutcomes/1",
                "value": reappearing,
            },
            {
                "op": "add",
                "path": "/protocolSection/outcomesModule/secondaryOutcomes/2",
                "value": added,
            },
        ]
        connection.execute(
            "INSERT INTO trial_versions VALUES ('NCT03734029', 29, ?)",
            (json.dumps(before),),
        )
        connection.execute(
            "INSERT INTO trial_versions VALUES ('NCT03734029', 30, ?)",
            (json.dumps(after),),
        )
        connection.execute(
            "INSERT INTO trial_patches VALUES ('NCT03734029', 29, 30, ?)",
            (json.dumps(patch),),
        )

        stats = compute_input_audit(connection)
        connection.close()

        self.assertEqual(stats["patches"], 1)
        self.assertEqual(stats["secondary_candidates"], 1)
        self.assertEqual(stats["corrected_secondary_memberships"], 1)
        self.assertEqual(stats["historical_v02_secondary_memberships"], 0)
        self.assertEqual(
            stats["v02_vs_corrected_secondary_disagreements"],
            ["NCT03734029_v29_v30"],
        )
        self.assertEqual(stats["primary_relevant_patches"], 0)
        self.assertEqual(stats["primary_literal_vs_state_disagreements"], [])
        self.assertEqual(stats["classified_records"], 1)
        self.assertEqual(stats["classified_trials"], 1)
        self.assertEqual(stats["event_class_memberships"], 1)
        self.assertEqual(
            stats["event_class_counts"],
            {"secondary_outcome_removed_after_primary_completion": 1},
        )

    def test_whole_array_operation_is_in_the_independent_candidate_denominator(self) -> None:
        connection = self.new_connection()
        removed = {"measure": "Quality of life", "timeFrame": "12 months"}
        before = record([removed])
        after = record([])
        del after["protocolSection"]["outcomesModule"]["secondaryOutcomes"]
        patch = [{"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes"}]
        connection.execute(
            "INSERT INTO trial_versions VALUES ('NCT00000001', 1, ?)",
            (json.dumps(before),),
        )
        connection.execute(
            "INSERT INTO trial_versions VALUES ('NCT00000001', 2, ?)",
            (json.dumps(after),),
        )
        connection.execute(
            "INSERT INTO trial_patches VALUES ('NCT00000001', 1, 2, ?)",
            (json.dumps(patch),),
        )

        stats = compute_input_audit(connection)
        connection.close()

        self.assertEqual(stats["secondary_candidates"], 1)
        self.assertEqual(stats["corrected_secondary_memberships"], 1)
        self.assertEqual(stats["historical_v02_secondary_memberships"], 0)
        self.assertEqual(
            stats["v02_vs_corrected_secondary_disagreements"],
            ["NCT00000001_v1_v2"],
        )
        self.assertEqual(stats["classified_records"], 1)
        self.assertEqual(stats["classified_trials"], 1)
        self.assertEqual(stats["event_class_memberships"], 1)
        self.assertEqual(
            stats["event_class_counts"],
            {"secondary_outcome_removed_after_primary_completion": 1},
        )


if __name__ == "__main__":
    unittest.main()
