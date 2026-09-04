from datetime import datetime, timezone

from app.audit import AuditStore


def test_audit_store_records_and_reads_event(tmp_path):
    database_path = tmp_path / "audit.db"
    store = AuditStore(str(database_path))

    timestamp = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)

    event_id = store.record_event(
        timestamp=timestamp,
        stage="policy",
        event_type="policy_evaluation",
        input_data={
            "source_order_id": "order_test",
            "amount": 20000,
        },
        decision="ALLOW",
        reasoning="Uplift is within the configured policy limit.",
        output_data={
            "rule_id": "all_policy_rules_passed",
        },
    )

    assert event_id == 1

    events = store.list_events()

    assert events == [
        {
            "id": 1,
            "timestamp": "2026-09-05T12:00:00+00:00",
            "stage": "policy",
            "event_type": "policy_evaluation",
            "input_data": {
                "source_order_id": "order_test",
                "amount": 20000,
            },
            "decision": "ALLOW",
            "reasoning": "Uplift is within the configured policy limit.",
            "output_data": {
                "rule_id": "all_policy_rules_passed",
            },
        }
    ]


def test_audit_store_preserves_multiple_events_in_order(tmp_path):
    store = AuditStore(str(tmp_path / "audit.db"))

    timestamp = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)

    first_id = store.record_event(
        timestamp=timestamp,
        stage="opportunity",
        event_type="opportunity_detected",
        input_data={"order_count": 3},
        reasoning="High-value order detected.",
        output_data={"opportunity_count": 1},
    )

    second_id = store.record_event(
        timestamp=timestamp,
        stage="policy",
        event_type="policy_evaluation",
        input_data={"opportunity_count": 1},
        decision="BLOCK",
        reasoning="Uplift exceeds the configured limit.",
        output_data={"rule_id": "maximum_uplift_ratio_exceeded"},
    )

    assert first_id == 1
    assert second_id == 2

    events = store.list_events()

    assert [event["stage"] for event in events] == [
        "opportunity",
        "policy",
    ]

    assert events[1]["decision"] == "BLOCK"