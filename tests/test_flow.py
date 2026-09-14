"""Exercise token → discovery → import → repeat/review/rollback using real connector functions."""

from contextlib import nullcontext
from decimal import Decimal

import pytest
from test_client import Response, Session

from wise_bank_feed.client import WiseClient

BALANCE = {
    "id": 64,
    "currency": "GBP",
    "type": "STANDARD",
    "name": None,
    "investmentState": "NOT_INVESTED",
    "amount": {"value": "120.30", "currency": "GBP"},
}
ACTIVITY = {
    "id": "activity-1",
    "type": "CARD_PAYMENT",
    "resource": {"id": 88, "type": "CARD_TRANSACTION"},
    "title": "<strong>Coffee</strong>",
    "description": "",
    "primaryAmount": "10 GBP",
    "secondaryAmount": "",
    "status": "COMPLETED",
    "createdOn": "2026-09-02T12:00:00Z",
    "updatedOn": "2026-09-02T12:00:00Z",
}
LINE = {
    "referenceNumber": "CARD-88",
    "type": "DEBIT",
    "date": "2026-09-02T12:00:00Z",
    "amount": {"value": "-10.30", "currency": "GBP"},
    "totalFees": {"value": "0.30", "currency": "GBP"},
    "details": {"description": "Coffee"},
    "exchangeDetails": None,
    "runningBalance": {"value": "120.30", "currency": "GBP"},
}


def feed(flow, monkeypatch, responses):
    session = Session(responses)
    client = WiseClient("offline-test-token", session=session)
    monkeypatch.setattr(flow.sync, "client_for", lambda c: nullcontext(client))
    monkeypatch.setattr(flow.api, "client_for", lambda c: nullcontext(client))
    return session


def mapped(flow, mode="Statements"):
    flow.db.set_value("Wise Connection", "conn", "mode", mode)
    flow.sync.discover(
        flow.frappe.get_doc("Wise Connection", "conn"),
        WiseClient("offline-test-token", session=Session([Response([BALANCE])])),
    )
    m = flow.rows("Wise Account Map")[0]
    flow.db.set_value("Wise Account Map", m["name"], "bank_account", "bank")
    flow.db.set_value("Wise Account Map", m["name"], "enabled", 1)
    flow.db.commit()
    return m["name"]


def test_token_discovery_and_activity_sync_without_any_mapping(flow, monkeypatch):
    flow.db.set_value("Wise Connection", "conn", "enabled", 0)
    session = feed(
        flow,
        monkeypatch,
        [
            Response([{"id": 9, "type": "personal"}, {"id": 123, "type": "business"}]),
            Response([{"id": 123, "type": "business"}]),
            Response([BALANCE]),
            Response([BALANCE]),
            Response({"activities": [ACTIVITY], "cursor": None}),
        ],
    )
    assert flow.api.profiles("conn") == [{"id": 123, "type": "business"}]
    maps = flow.api.discover_accounts("conn")
    assert len(maps) == 1 and maps[0]["enabled"] == 0 and maps[0]["bank_account"] is None
    flow.db.set_value("Wise Connection", "conn", "enabled", 1)
    flow.db.commit()
    flow.sync.run("conn")
    assert len(flow.rows("Wise Activity")) == 1
    assert flow.rows("Bank Transaction") == []
    assert flow.rows("Wise Sync Log")[-1]["result"] == "Success"
    assert all(url.startswith("https://api.wise.com/2026Q3/") for url, _ in session.calls)
    assert all(k["headers"]["Authorization"] == "Bearer offline-test-token" for _, k in session.calls)
    assert "offline-test-token" not in str(flow.db.rows)


def test_repeated_activity_sync_preserves_finished_review(flow, monkeypatch):
    for attempt in range(2):
        feed(flow, monkeypatch, [Response([BALANCE]), Response({"activities": [ACTIVITY], "cursor": None})])
        flow.sync.run("conn")
        assert flow.rows("Wise Sync Log")[-1]["result"] == "Success"
        row = flow.rows("Wise Activity")[0]
        if attempt:
            assert row["needs_review"] == 0
        flow.api.finish_review(row["name"], "Checked in Wise", row["payload_hash"])
        flow.db.commit()
    assert len(flow.rows("Wise Activity")) == 1
    assert flow.rows("Wise Activity")[0]["needs_review"] == 0
    assert flow.rows("Bank Transaction") == []


def test_later_page_failure_rolls_back_discovery_and_activities(flow, monkeypatch):
    feed(
        flow,
        monkeypatch,
        [
            Response([BALANCE]),
            Response({"activities": [ACTIVITY], "cursor": "next"}),
            Response({"private": "must not leak"}, 403, {"x-2fa-approval": "secret-challenge"}),
        ],
    )
    flow.sync.run("conn")
    assert flow.rows("Wise Activity") == []
    assert flow.rows("Wise Account Map") == []
    assert flow.rows("Wise Connection")[0].get("cursor_at") is None
    assert flow.rows("Wise Sync Log")[-1]["result"] == "Error"
    assert "secret-challenge" not in str(flow.db.rows) and "must not leak" not in str(flow.db.rows)


def test_statement_repeat_imports_once_and_does_not_double_count_fees(flow, monkeypatch):
    mapped(flow)
    for _ in range(2):
        feed(flow, monkeypatch, [Response([BALANCE]), Response({"transactions": [LINE]})])
        flow.sync.run("conn")
        assert flow.rows("Wise Sync Log")[-1]["result"] == "Success"
    assert len(flow.rows("Wise Booking")) == len(flow.rows("Bank Transaction")) == 1
    bank = flow.rows("Bank Transaction")[0]
    assert bank["withdrawal"] == Decimal("10.30") and bank["deposit"] == 0 and bank["docstatus"] == 1


def test_second_account_failure_rolls_back_first_account_bookings_and_checkpoint(flow, monkeypatch):
    first = mapped(flow)
    second_balance = BALANCE | {"id": 65, "name": "Tax jar", "type": "SAVINGS"}
    flow.seed(
        "Wise Account Map",
        "second",
        connection="conn",
        balance_id="65",
        currency="GBP",
        source_key="second-key",
        bank_account="bank",
        enabled=1,
        available=1,
    )
    # Discovery finds the same identity as the seeded map.
    from wise_bank_feed.core import key

    flow.db.set_value("Wise Account Map", "second", "source_key", key("Production", "123", "65"))
    flow.db.commit()
    feed(
        flow,
        monkeypatch,
        [
            Response([BALANCE, second_balance]),
            Response({"transactions": [LINE]}),
            Response({}, 403, {"x-2fa-approval": "challenge"}),
        ],
    )
    flow.sync.run("conn")
    assert flow.rows("Bank Transaction") == [] and flow.rows("Wise Booking") == []
    assert flow.db.rows["Wise Account Map", first].get("cursor_at") is None
    assert flow.db.rows["Wise Account Map", "second"].get("cursor_at") is None
    assert flow.rows("Wise Sync Log")[-1]["result"] == "Error"


def test_duplicate_statement_references_roll_back_window(flow, monkeypatch):
    mapped(flow)
    feed(flow, monkeypatch, [Response([BALANCE]), Response({"transactions": [LINE, LINE]})])
    flow.sync.run("conn")
    assert flow.rows("Bank Transaction") == [] and flow.rows("Wise Booking") == []
    assert flow.rows("Wise Account Map")[0].get("cursor_at") is None


def test_discovery_updates_names_without_overwriting_mapping_or_deleting_missing_accounts(flow, monkeypatch):
    name = mapped(flow)
    feed(
        flow, monkeypatch, [Response([BALANCE | {"name": "Working capital"}]), Response({"transactions": []})]
    )
    flow.sync.run("conn")
    row = flow.db.rows["Wise Account Map", name]
    assert row["account_name"] == "Working capital" and row["bank_account"] == "bank" and row["enabled"] == 1
    feed(flow, monkeypatch, [Response([])])
    # Discovery itself marks unavailable; a statement run with zero mappings rolls back by design.
    with flow.sync.client_for(None) as client:
        flow.sync.discover(flow.frappe.get_doc("Wise Connection", "conn"), client)
    assert flow.db.rows["Wise Account Map", name]["available"] == 0
    assert flow.db.rows["Wise Account Map", name]["bank_account"] == "bank"


def reviewed_args(flow):
    name = mapped(flow, "Activity Review")
    c = flow.frappe.get_doc("Wise Connection", "conn")
    doc = flow.sync.ingest_activity(c, ACTIVITY)
    return dict(
        activity=doc.name,
        account_map=name,
        direction="Withdrawal",
        value="10.30",
        booking_date="2026-09-02",
        evidence="Verified booked total in Wise",
        expected_hash=doc.payload_hash,
        confirmed=1,
    )


def test_reviewed_booking_is_explicit_and_repeated_click_does_not_duplicate(flow):
    args = reviewed_args(flow)
    bank = flow.api.create_reviewed_booking(**args)
    with pytest.raises(ValueError, match="already exists"):
        flow.api.create_reviewed_booking(**args)
    assert len(flow.rows("Bank Transaction")) == 1
    assert flow.db.rows["Bank Transaction", bank]["withdrawal"] == Decimal("10.30")
    assert flow.rows("Wise Activity")[0]["needs_review"] == 1


@pytest.mark.parametrize(
    "override",
    [
        dict(confirmed=0),
        dict(evidence=" "),
        dict(value="0"),
        dict(value="-1"),
        dict(value="NaN"),
        dict(direction="Unknown"),
        dict(expected_hash="stale"),
        dict(booking_date="2026-09-15"),
    ],
)
def test_invalid_review_never_creates_bank_entry(flow, override):
    args = reviewed_args(flow)
    with pytest.raises(ValueError):
        flow.api.create_reviewed_booking(**(args | override))
    assert flow.rows("Bank Transaction") == []


def test_activity_revision_holds_booking_until_acknowledged(flow):
    args = reviewed_args(flow)
    bank = flow.api.create_reviewed_booking(**args)
    c = flow.frappe.get_doc("Wise Connection", "conn")
    flow.sync.ingest_activity(c, ACTIVITY | {"primaryAmount": "11 GBP"})
    booking = flow.rows("Wise Booking")[0]
    assert booking["needs_review"] == 1
    assert flow.db.rows["Bank Transaction", bank]["custom_wise_review"] == 1
    assert flow.db.rows["Bank Transaction", bank]["withdrawal"] == Decimal("10.30")
    with pytest.raises(ValueError, match="Source changed"):
        flow.api.acknowledge_change(booking["name"], "Checked", "stale")
    flow.api.acknowledge_change(booking["name"], "Adjustment recorded", booking["latest_hash"])
    flow.sync.ingest_activity(c, ACTIVITY | {"primaryAmount": "11 GBP"})
    assert flow.rows("Wise Booking")[0]["needs_review"] == 0
    assert flow.db.rows["Bank Transaction", bank]["custom_wise_review"] == 0


@pytest.mark.parametrize("action", ["profiles", "discover_accounts", "sync_now"])
def test_non_manager_cannot_access_token_or_start_sync(flow, action):
    flow.roles.clear()
    with pytest.raises(ValueError, match="Not permitted"):
        getattr(flow.api, action)("conn")


def test_blank_review_booking_date_is_rejected_instead_of_defaulting_to_today(flow):
    args = reviewed_args(flow)
    with pytest.raises(ValueError, match="date"):
        flow.api.create_reviewed_booking(**(args | {"booking_date": ""}))
    assert flow.rows("Bank Transaction") == []


def test_disabled_connection_does_not_fetch_or_import(flow, monkeypatch):
    flow.db.set_value("Wise Connection", "conn", "enabled", 0)
    session = feed(flow, monkeypatch, [])
    flow.sync.run("conn")
    assert session.calls == [] and flow.rows("Wise Sync Log") == []


def test_selected_business_profile_must_belong_to_token(flow, monkeypatch):
    flow.db.set_value("Wise Connection", "conn", "enabled", 0)
    feed(flow, monkeypatch, [Response([{"id": 999, "type": "business"}])])
    with pytest.raises(ValueError, match="does not expose"):
        flow.api.discover_accounts("conn")
    assert flow.rows("Wise Account Map") == []


def test_scheduler_queues_only_enabled_connections_after_commit(flow, monkeypatch):
    flow.seed("Wise Connection", "paused", enabled=0)
    queued = []
    monkeypatch.setattr(
        flow.frappe, "enqueue", lambda method, **kw: queued.append((method, kw)), raising=False
    )
    flow.sync.schedule()
    assert queued == [
        (
            "wise_bank_feed.sync.run",
            dict(
                connection="conn",
                queue="long",
                timeout=900,
                job_id="wise-sync-conn",
                deduplicate=True,
                enqueue_after_commit=True,
            ),
        )
    ]


@pytest.mark.parametrize("audit_recent", [False, True])
def test_caught_up_sync_rechecks_old_activity_weekly_only(flow, monkeypatch, audit_recent):
    flow.db.set_value("Wise Connection", "conn", "start_date", "2026-01-01")
    flow.db.set_value("Wise Connection", "conn", "cursor_at", "2026-09-30T12:00:00")
    if audit_recent:
        flow.db.set_value("Wise Connection", "conn", "audit_at", "2026-09-30T12:00:00")
    flow.db.commit()
    responses = [Response([BALANCE]), Response({"activities": [], "cursor": None})]
    if not audit_recent:
        responses.append(Response({"activities": [ACTIVITY], "cursor": None}))
    session = feed(flow, monkeypatch, responses)
    flow.sync.run("conn")
    assert flow.rows("Wise Sync Log")[-1]["result"] == "Success"
    assert len(flow.rows("Wise Activity")) == (0 if audit_recent else 1)
    calls = [kw["params"] for url, kw in session.calls if url.endswith("/activities")]
    assert len(calls) == (1 if audit_recent else 2)
    if not audit_recent:
        assert calls[1]["since"] == "2026-07-03T12:00:00+00:00"
        assert calls[1]["until"] == "2026-10-01T12:00:00+00:00"
