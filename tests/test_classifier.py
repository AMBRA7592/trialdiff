from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from trialdiff.classifier.materiality import ClassifierRule, classify_patch
from trialdiff.classifier.pathmatch import match_path
from trialdiff.classifier.timing import timing_context_from_status
from trialdiff.db import TrialDiffStore, connect, init_db


FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def load_seeded_rules() -> list[ClassifierRule]:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/trialdiff.sqlite3"
        init_db(db_path)
        connection = connect(db_path)
        try:
            store = TrialDiffStore(connection)
            return [ClassifierRule.from_row(row) for row in store.load_active_rules()]
        finally:
            connection.close()


class ClassifierTests(unittest.TestCase):
    def test_path_matcher_single_and_multi_segment_globs(self) -> None:
        path = "/protocolSection/outcomesModule/primaryOutcomes/0/measure"

        self.assertTrue(match_path("/protocolSection/outcomesModule/primaryOutcomes/**", path))
        self.assertTrue(match_path("/protocolSection/outcomesModule/primaryOutcomes/*/measure", path))
        self.assertFalse(match_path("/protocolSection/outcomesModule/primaryOutcomes/*", path))

    def test_timing_context_status_mapping(self) -> None:
        self.assertEqual(timing_context_from_status("NOT_YET_RECRUITING"), "pre_recruitment")
        self.assertEqual(timing_context_from_status("RECRUITING"), "early_recruitment")
        self.assertEqual(timing_context_from_status("ACTIVE_NOT_RECRUITING"), "late_recruitment")
        self.assertEqual(timing_context_from_status("COMPLETED"), "post_recruitment")
        self.assertEqual(timing_context_from_status("TERMINATED"), "post_recruitment")
        self.assertEqual(timing_context_from_status("AVAILABLE"), "unknown")

    def test_primary_outcome_patch_classifies_critical(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        patch = load_fixture("patch_to_next.json")

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=1,
            to_version=2,
            from_record=from_study,
            patch=patch,
            rules=rules,
            submitted_date="2021-11-05",
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity_pre_timing, "critical")
        self.assertEqual(event.severity, "critical")
        self.assertEqual(event.category, "primary_outcome_change")
        self.assertIn("enrollment_change", event.categories)
        self.assertIn("primary_outcome_change", event.categories)
        self.assertIn("primary_outcome_any_change", event.deterministic_rules)
        self.assertEqual(event.timing_context, "early_recruitment")
        self.assertTrue(event.rule_set_hash)

    def test_secondary_outcome_late_recruitment_escalates_to_critical(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["overallStatus"] = "ACTIVE_NOT_RECRUITING"
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/outcomesModule/secondaryOutcomes/0/measure",
                "value": "Serious adverse events",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=3,
            to_version=4,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity_pre_timing, "high")
        self.assertEqual(event.severity, "critical")
        self.assertEqual(event.timing_context, "late_recruitment")
        self.assertEqual(event.category, "secondary_outcome_change")

    def test_empty_why_stopped_value_signal_is_critical(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["overallStatus"] = "TERMINATED"
        patch = [{"op": "add", "path": "/protocolSection/statusModule/whyStopped", "value": ""}]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=5,
            to_version=6,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity_pre_timing, "critical")
        self.assertEqual(event.severity, "critical")
        self.assertEqual(event.category, "status_termination")
        self.assertEqual(event.value_signals[0]["signal"], "why_stopped_empty")

    def test_missing_why_stopped_value_signal_is_critical(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["overallStatus"] = "TERMINATED"
        from_study["protocolSection"]["statusModule"]["whyStopped"] = "Sponsor decision"
        patch = [{"op": "remove", "path": "/protocolSection/statusModule/whyStopped"}]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.value_signals[0]["signal"], "why_stopped_empty")
        self.assertEqual(event.severity, "critical")

    def test_low_information_why_stopped_phrase_is_flagged(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        patch = [
            {
                "op": "add",
                "path": "/protocolSection/statusModule/whyStopped",
                "value": "Study is being closed because PI left Emory",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.value_signals[0]["signal"], "why_stopped_low_information")
        self.assertEqual(event.value_signals[0]["severity"], "high")

    def test_timeline_minor_date_adjustment_is_low(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["primaryCompletionDateStruct"] = {
            "date": "2026-01-01",
            "type": "ESTIMATED",
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/statusModule/primaryCompletionDateStruct/date",
                "value": "2026-01-20",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity_pre_timing, "low")
        self.assertEqual(event.severity, "low")
        self.assertEqual(event.category, "timeline_minor_adjustment")
        self.assertEqual(event.value_signals[0]["delta_days"], 19)
        self.assertEqual(event.value_signals[0]["direction"], "later")

    def test_timeline_30_to_90_day_shift_is_medium(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["completionDateStruct"] = {
            "date": "2026-01-01",
            "type": "ESTIMATED",
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/statusModule/completionDateStruct/date",
                "value": "2026-03-01",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity, "medium")
        self.assertEqual(event.category, "timeline_shift")
        self.assertEqual(event.value_signals[0]["delta_days"], 59)

    def test_timeline_90_to_365_day_shift_is_high(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["completionDateStruct"] = {
            "date": "2026-01-01",
            "type": "ESTIMATED",
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/statusModule/completionDateStruct/date",
                "value": "2026-06-01",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity, "high")
        self.assertEqual(event.category, "timeline_significant_shift")
        self.assertEqual(event.value_signals[0]["delta_days"], 151)

    def test_timeline_major_slip_can_escalate_with_timing(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["overallStatus"] = "ACTIVE_NOT_RECRUITING"
        from_study["protocolSection"]["statusModule"]["completionDateStruct"] = {
            "date": "2026-01-01",
            "type": "ESTIMATED",
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/statusModule/completionDateStruct/date",
                "value": "2027-03-01",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity_pre_timing, "high")
        self.assertEqual(event.severity, "critical")
        self.assertEqual(event.category, "timeline_major_slip")
        self.assertEqual(event.value_signals[0]["delta_days"], 424)
        self.assertEqual(event.value_signals[0]["direction"], "later")

    def test_estimated_to_actual_without_date_movement_is_low_milestone(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["primaryCompletionDateStruct"] = {
            "date": "2026-01-01",
            "type": "ESTIMATED",
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/statusModule/primaryCompletionDateStruct/type",
                "value": "ACTUAL",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity, "low")
        self.assertEqual(event.category, "milestone_realized")
        self.assertEqual(event.value_signals[0]["signal"], "milestone_realized")

    def test_actual_date_correction_stays_low_even_with_large_delta(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["overallStatus"] = "COMPLETED"
        from_study["protocolSection"]["statusModule"]["completionDateStruct"] = {
            "date": "2026-01-01",
            "type": "ACTUAL",
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/statusModule/completionDateStruct/date",
                "value": "2024-01-01",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity_pre_timing, "low")
        self.assertEqual(event.severity, "low")
        self.assertEqual(event.category, "timeline_actual_date_correction")
        self.assertEqual(event.value_signals[0]["signal"], "timeline_actual_date_correction")
        self.assertEqual(event.value_signals[0]["direction"], "earlier")

    def test_estimated_to_actual_earlier_date_is_low_actualization(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["primaryCompletionDateStruct"] = {
            "date": "2028-12-31",
            "type": "ESTIMATED",
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/statusModule/primaryCompletionDateStruct/date",
                "value": "2022-12-31",
            },
            {
                "op": "replace",
                "path": "/protocolSection/statusModule/primaryCompletionDateStruct/type",
                "value": "ACTUAL",
            },
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity, "low")
        self.assertEqual(event.category, "timeline_actualized_earlier")
        self.assertEqual(event.value_signals[0]["signal"], "timeline_actualized_earlier")
        self.assertEqual(event.value_signals[0]["direction"], "earlier")

    def test_review_unit_metadata_alone_does_not_trigger_secondary_outcome_change(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        patch = [
            {
                "op": "add",
                "path": "/protocolSection/outcomesModule/secondaryOutcomes/0/reviewUnit",
                "value": {
                    "resetReasons": [
                        "The Time Frame appears inconsistent with information provided here or in other parts of the record."
                    ]
                },
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNone(event)

    def test_serious_adverse_event_addition_is_high(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["resultsSection"] = {"adverseEventsModule": {"seriousEvents": []}}
        patch = [
            {
                "op": "add",
                "path": "/resultsSection/adverseEventsModule/seriousEvents/0",
                "value": {"groupId": "EG001", "numAffected": 1, "numAtRisk": 3, "numEvents": 1},
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity, "high")
        self.assertEqual(event.category, "serious_adverse_event_addition")
        self.assertIn("serious_adverse_event_addition", event.deterministic_rules)

    def test_serious_adverse_event_removal_is_critical(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["resultsSection"] = {
            "adverseEventsModule": {
                "seriousEvents": [{"stats": [{"groupId": "EG000", "numAffected": 1}]}]
            }
        }
        patch = [{"op": "remove", "path": "/resultsSection/adverseEventsModule/seriousEvents/0"}]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity, "critical")
        self.assertEqual(event.category, "serious_adverse_event_removal")
        self.assertIn("serious_adverse_event_removal", event.deterministic_rules)

    def test_other_adverse_event_removal_is_high(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["resultsSection"] = {
            "adverseEventsModule": {
                "otherEvents": [{"stats": [{"groupId": "EG000", "numAffected": 2}]}]
            }
        }
        patch = [{"op": "remove", "path": "/resultsSection/adverseEventsModule/otherEvents/0"}]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity, "high")
        self.assertEqual(event.category, "other_adverse_event_removal")
        self.assertIn("other_adverse_event_removal", event.deterministic_rules)

    def test_adverse_event_group_change_is_high(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["resultsSection"] = {"adverseEventsModule": {"eventGroups": []}}
        patch = [
            {
                "op": "add",
                "path": "/resultsSection/adverseEventsModule/eventGroups/1",
                "value": {"deathsNumAffected": 0, "seriousNumAffected": 2, "seriousNumAtRisk": 3},
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=6,
            to_version=7,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity, "high")
        self.assertEqual(event.category, "adverse_event_group_change")
        self.assertIn("adverse_event_group_change", event.deterministic_rules)

    def test_timing_modifier_does_not_escalate_low_admin_change(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        from_study["protocolSection"]["statusModule"]["overallStatus"] = "COMPLETED"
        from_study["protocolSection"]["contactsLocationsModule"] = {
            "centralContacts": [{"name": "Old Contact"}]
        }
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/contactsLocationsModule/centralContacts/0/name",
                "value": "New Contact",
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=7,
            to_version=8,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.severity_pre_timing, "low")
        self.assertEqual(event.severity, "low")
        self.assertEqual(event.timing_context, "post_recruitment")
        self.assertEqual(event.category, "administrative_contact_change")

    def test_enrollment_threshold_boundary(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        patch_19 = [
            {
                "op": "replace",
                "path": "/protocolSection/designModule/enrollmentInfo/count",
                "value": 98,
            }
        ]
        patch_20 = [
            {
                "op": "replace",
                "path": "/protocolSection/designModule/enrollmentInfo/count",
                "value": 96,
            }
        ]

        event_19 = classify_patch(
            nct_id="NCT00000001",
            from_version=8,
            to_version=9,
            from_record=from_study,
            patch=patch_19,
            rules=rules,
        )
        event_20 = classify_patch(
            nct_id="NCT00000001",
            from_version=9,
            to_version=10,
            from_record=from_study,
            patch=patch_20,
            rules=rules,
        )

        self.assertIsNotNone(event_19)
        self.assertFalse(event_19.value_signals if event_19 else None)
        self.assertIsNotNone(event_20)
        assert event_20 is not None
        self.assertEqual(event_20.value_signals[0]["signal"], "enrollment_count_change_ge_20pct")

    def test_enrollment_zeroed_is_critical_value_signal(self) -> None:
        rules = load_seeded_rules()
        from_study = load_fixture("from_study.json")
        patch = [
            {
                "op": "replace",
                "path": "/protocolSection/designModule/enrollmentInfo/count",
                "value": 0,
            }
        ]

        event = classify_patch(
            nct_id="NCT00000001",
            from_version=10,
            to_version=11,
            from_record=from_study,
            patch=patch,
            rules=rules,
        )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.value_signals[0]["signal"], "enrollment_zeroed")
        self.assertEqual(event.severity_pre_timing, "critical")


if __name__ == "__main__":
    unittest.main()
