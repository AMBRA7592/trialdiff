from __future__ import annotations

import unittest

from trialdiff.event_classes import (
    EventClassInputError,
    OUTCOME_EDIT_WITH_RESULTS_SIGNAL,
    PRIMARY_ENDPOINT_CLEAN,
    SECONDARY_OUTCOME_REMOVED,
    WHY_STOPPED_REMOVED_TERMINAL,
    event_classes_for_patch,
)


def record(
    *,
    status: str = "COMPLETED",
    has_results: bool = False,
    primary_outcomes: list[dict] | None = None,
    secondary_outcomes: list[dict] | None = None,
) -> dict:
    return {
        "hasResults": has_results,
        "protocolSection": {
            "statusModule": {"overallStatus": status},
            "outcomesModule": {
                "primaryOutcomes": (
                    [{"measure": "Overall survival"}] if primary_outcomes is None else primary_outcomes
                ),
                "secondaryOutcomes": [] if secondary_outcomes is None else secondary_outcomes,
            },
            "designModule": {},
        },
    }


class EventClassTests(unittest.TestCase):
    def test_secondary_outcome_reindex_is_not_treated_as_removal(self) -> None:
        moved = {"measure": "Quality of life", "description": "FACT-B score", "timeFrame": "12 months"}
        safety = {"measure": "Safety"}
        from_record = record(secondary_outcomes=[safety, moved])
        to_record = record(secondary_outcomes=[moved, safety])
        patch = [
            {"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes/0"},
            {
                "op": "add",
                "path": "/protocolSection/outcomesModule/secondaryOutcomes/1",
                "value": safety,
            },
        ]

        self.assertNotIn(
            SECONDARY_OUTCOME_REMOVED,
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
        )

    def test_secondary_outcome_absent_from_to_record_is_removal(self) -> None:
        removed = {"measure": "Quality of life", "description": "FACT-B score", "timeFrame": "12 months"}
        from_record = record(secondary_outcomes=[removed])
        to_record = record(secondary_outcomes=[])
        patch = [{"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes/0"}]

        self.assertIn(
            SECONDARY_OUTCOME_REMOVED,
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
        )

    def test_sequential_secondary_removals_resolve_against_evolving_array(self) -> None:
        reappearing = {"measure": "Cohort overall survival"}
        removed = {"measure": "All-patient overall survival"}
        retained = {"measure": "Progression-free survival"}
        added = {"measure": "Duration of response"}
        from_record = record(secondary_outcomes=[retained, reappearing, removed])
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
        to_record = record(secondary_outcomes=[retained, reappearing, added])

        self.assertIn(
            SECONDARY_OUTCOME_REMOVED,
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
        )

    def test_primary_outcome_reorder_is_not_definition_change(self) -> None:
        first = {"measure": "Overall survival", "timeFrame": "24 months"}
        second = {"measure": "Progression-free survival", "timeFrame": "24 months"}
        from_record = record(primary_outcomes=[first, second])
        patch = [
            {"op": "remove", "path": "/protocolSection/outcomesModule/primaryOutcomes/0"},
            {
                "op": "add",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/1",
                "value": first,
            },
        ]
        to_record = record(primary_outcomes=[second, first])

        self.assertNotIn(
            PRIMARY_ENDPOINT_CLEAN,
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
        )

    def test_primary_outcome_comparison_preserves_duplicate_counts(self) -> None:
        duplicate = {"measure": "Overall survival", "timeFrame": "24 months"}
        from_record = record(primary_outcomes=[duplicate, duplicate])
        patch = [{"op": "remove", "path": "/protocolSection/outcomesModule/primaryOutcomes/0"}]
        to_record = record(primary_outcomes=[duplicate])

        self.assertIn(
            PRIMARY_ENDPOINT_CLEAN,
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
        )

    def test_primary_outcome_definition_replacement_still_fires(self) -> None:
        from_record = record(primary_outcomes=[{"measure": "Overall survival"}])
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                "value": "Progression-free survival",
            }
        ]
        to_record = record(primary_outcomes=[{"measure": "Progression-free survival"}])

        self.assertIn(
            PRIMARY_ENDPOINT_CLEAN,
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
        )

    def test_malformed_primary_outcomes_array_is_rejected(self) -> None:
        from_record = record()
        from_record["protocolSection"]["outcomesModule"]["primaryOutcomes"] = {
            "0": {"measure": "Overall survival"}
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                "value": "Progression-free survival",
            }
        ]

        with self.assertRaises(EventClassInputError):
            event_classes_for_patch(from_record=from_record, to_record=None, patch=patch)

    def test_malformed_secondary_outcomes_array_is_rejected(self) -> None:
        from_record = record(secondary_outcomes=[{"measure": "Quality of life"}])
        patch = [
            {"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes/0"},
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/secondaryOutcomes",
                "value": {},
            },
        ]

        with self.assertRaises(EventClassInputError):
            event_classes_for_patch(from_record=from_record, to_record=None, patch=patch)

    def test_results_signal_is_a_cooccurrence_class_not_suppression(self) -> None:
        from_record = record(has_results=False, primary_outcomes=[{"measure": "Response rate"}])
        to_record = record(has_results=True, primary_outcomes=[{"measure": "Objective response rate"}])
        patch = [
            {"op": "replace", "path": "/hasResults", "value": True},
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                "value": "Objective response rate",
            },
        ]

        self.assertIn(
            OUTCOME_EDIT_WITH_RESULTS_SIGNAL,
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
        )

    def test_missing_to_record_without_patch_evidence_is_not_whystopped_removal(self) -> None:
        # Regression test for the v0.1/v0.1.1 package bug: a missing TO-version
        # snapshot must not be read as "whyStopped absent". Without patch
        # evidence, the class must not fire.
        from_record = record(status="TERMINATED")
        from_record["protocolSection"]["statusModule"]["whyStopped"] = "Recruitment failed"
        patch = [
            {"op": "add", "path": "/protocolSection/statusModule/statusVerifiedDate", "value": "2025-12"},
            {"op": "replace", "path": "/hasResults", "value": True},
        ]

        self.assertNotIn(
            WHY_STOPPED_REMOVED_TERMINAL,
            event_classes_for_patch(from_record=from_record, to_record=None, patch=patch),
        )

    def test_missing_to_record_with_patch_removal_is_whystopped_removal(self) -> None:
        from_record = record(status="TERMINATED")
        from_record["protocolSection"]["statusModule"]["whyStopped"] = "Recruitment failed"
        patch = [{"op": "remove", "path": "/protocolSection/statusModule/whyStopped"}]

        self.assertIn(
            WHY_STOPPED_REMOVED_TERMINAL,
            event_classes_for_patch(from_record=from_record, to_record=None, patch=patch),
        )

    def test_missing_to_record_with_patch_emptying_is_whystopped_removal(self) -> None:
        from_record = record(status="TERMINATED")
        from_record["protocolSection"]["statusModule"]["whyStopped"] = "Recruitment failed"
        patch = [{"op": "replace", "path": "/protocolSection/statusModule/whyStopped", "value": "  "}]

        self.assertIn(
            WHY_STOPPED_REMOVED_TERMINAL,
            event_classes_for_patch(from_record=from_record, to_record=None, patch=patch),
        )

    def test_stored_to_must_equal_patch_replay(self) -> None:
        from_record = record(status="TERMINATED")
        from_record["protocolSection"]["statusModule"]["whyStopped"] = "Recruitment failed"
        to_record = record(status="TERMINATED")
        patch = [{"op": "add", "path": "/protocolSection/statusModule/statusVerifiedDate", "value": "2025-12"}]

        with self.assertRaises(EventClassInputError):
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch)

    def test_replay_failure_is_not_secondary_removal_evidence(self) -> None:
        from_record = record(secondary_outcomes=[{"measure": "Quality of life"}])
        patch = [
            {"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes/0"},
            {"op": "move", "from": "/unsupported", "path": "/unsupported-target"},
        ]

        with self.assertRaises(EventClassInputError):
            event_classes_for_patch(from_record=from_record, to_record=None, patch=patch)

    def test_replay_failure_is_not_primary_change_evidence(self) -> None:
        from_record = record(primary_outcomes=[{"measure": "Overall survival"}])
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/primaryOutcomes/0/measure",
                "value": "Progression-free survival",
            },
            {"op": "copy", "from": "/unsupported", "path": "/unsupported-target"},
        ]

        with self.assertRaises(EventClassInputError):
            event_classes_for_patch(from_record=from_record, to_record=None, patch=patch)

    def test_supported_operation_requires_a_string_path(self) -> None:
        with self.assertRaises(EventClassInputError):
            event_classes_for_patch(
                from_record=record(),
                to_record=None,
                patch=[{"op": "replace", "path": None, "value": "invalid"}],
            )

    def test_add_and_replace_operations_require_values(self) -> None:
        for op in ("add", "replace"):
            with self.subTest(op=op), self.assertRaises(EventClassInputError):
                event_classes_for_patch(
                    from_record=record(),
                    to_record=None,
                    patch=[{"op": op, "path": "/hasResults"}],
                )

    def test_event_classes_are_returned_in_sorted_order(self) -> None:
        removed = {"measure": "Quality of life", "description": "FACT-B score", "timeFrame": "12 months"}
        from_record = record(
            status="TERMINATED",
            has_results=False,
            primary_outcomes=[{"measure": "Overall survival"}],
            secondary_outcomes=[removed],
        )
        from_record["protocolSection"]["statusModule"]["whyStopped"] = "Recruitment failed"
        from_record["protocolSection"]["statusModule"]["primaryCompletionDateStruct"] = {"type": "ACTUAL"}
        to_record = record(
            status="TERMINATED",
            has_results=True,
            primary_outcomes=[{"measure": "Overall survival"}],
            secondary_outcomes=[],
        )
        to_record["protocolSection"]["statusModule"]["primaryCompletionDateStruct"] = {"type": "ACTUAL"}
        patch = [
            {"op": "remove", "path": "/protocolSection/statusModule/whyStopped"},
            {"op": "replace", "path": "/hasResults", "value": True},
            {"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes/0"},
        ]

        self.assertEqual(
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
            sorted([OUTCOME_EDIT_WITH_RESULTS_SIGNAL, SECONDARY_OUTCOME_REMOVED, WHY_STOPPED_REMOVED_TERMINAL]),
        )


if __name__ == "__main__":
    unittest.main()
