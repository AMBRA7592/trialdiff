from __future__ import annotations

import unittest

from trialdiff.event_classes import (
    OUTCOME_EDIT_WITH_RESULTS_SIGNAL,
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
                "primaryOutcomes": primary_outcomes or [{"measure": "Overall survival"}],
                "secondaryOutcomes": secondary_outcomes or [],
            },
            "designModule": {},
        },
    }


class EventClassTests(unittest.TestCase):
    def test_secondary_outcome_reindex_is_not_treated_as_removal(self) -> None:
        moved = {"measure": "Quality of life", "description": "FACT-B score", "timeFrame": "12 months"}
        from_record = record(secondary_outcomes=[{"measure": "Safety"}, moved])
        to_record = record(secondary_outcomes=[moved])
        patch = [{"op": "remove", "path": "/protocolSection/outcomesModule/secondaryOutcomes/1"}]

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
            {"op": "replace", "path": "/protocolSection/statusModule/statusVerifiedDate", "value": "2025-12"},
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

    def test_to_record_showing_removal_fires_without_patch_op(self) -> None:
        # Two stored snapshots are direct evidence; no patch op is required.
        from_record = record(status="TERMINATED")
        from_record["protocolSection"]["statusModule"]["whyStopped"] = "Recruitment failed"
        to_record = record(status="TERMINATED")
        patch = [{"op": "replace", "path": "/protocolSection/statusModule/statusVerifiedDate", "value": "2025-12"}]

        self.assertIn(
            WHY_STOPPED_REMOVED_TERMINAL,
            event_classes_for_patch(from_record=from_record, to_record=to_record, patch=patch),
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
