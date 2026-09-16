import importlib
import sys

import pytest
from test_client import Response, Session

from wise_bank_feed.client import WiseError


@pytest.fixture
def setup(flow, monkeypatch):
    monkeypatch.delitem(sys.modules, "wise_bank_feed.setup", raising=False)
    module = importlib.import_module("wise_bank_feed.setup")
    return module


def test_profile_labels_keep_ids_without_returning_private_fields(setup):
    result = setup.business_profiles(
        [
            {"id": 12, "type": "business", "details": {"name": "Wharf Ltd"}, "secret": "omit"},
            {"id": 13, "type": "personal"},
            {"id": 14, "type": "BUSINESS"},
        ]
    )
    assert result == [{"id": "12", "label": "Wharf Ltd"}, {"id": "14", "label": "Business profile 14"}]


def test_mapping_rejects_other_connection(setup, flow):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed("Wise Account Map", "foreign", connection="other")
    with pytest.raises(ValueError, match="another connection"):
        setup.save_mappings("conn", [{"name": "foreign", "bank_account": "bank"}])


def test_mapping_changes_require_pause(setup, flow):
    with pytest.raises(ValueError, match="Pause"):
        setup.save_mappings("conn", [])


@pytest.mark.parametrize("available", [0, 1])
@pytest.mark.parametrize("bank_account", ["bank", ""])
def test_skipping_booked_account_preserves_mapping(setup, flow, monkeypatch, available, bank_account):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed(
        "Wise Account Map",
        "map",
        connection="conn",
        currency="GBP",
        available=available,
        enabled=1,
        bank_account="bank",
    )
    flow.seed("Wise Booking", "booking", account_map="map", connection="conn")
    original_save = flow.Doc.save

    def validated_save(doc, **kwargs):
        if doc.doctype == "Wise Account Map":
            # The storage double normally skips controllers; exercise the real historical guard here.
            flow.documents.AccountMap.validate(doc)
        return original_save(doc, **kwargs)

    monkeypatch.setattr(flow.Doc, "save", validated_save)
    setup.save_mappings("conn", [{"name": "map", "bank_account": bank_account, "enabled": 0}])
    assert flow.db.rows["Wise Account Map", "map"]["enabled"] == 0
    assert flow.db.rows["Wise Account Map", "map"]["bank_account"] == "bank"


def test_unmapped_accounts_can_remain_skipped(setup, flow):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed("Wise Account Map", "map", connection="conn", available=1, enabled=0)
    setup.save_mappings("conn", [{"name": "map", "bank_account": "", "enabled": 0}])
    assert flow.db.rows["Wise Account Map", "map"]["enabled"] == 0
    assert not flow.db.rows["Wise Account Map", "map"]["bank_account"]


def test_enabled_account_requires_a_mapping(setup, flow):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed("Wise Account Map", "map", connection="conn", available=1, enabled=0)
    with pytest.raises(ValueError, match="Bank Account"):
        setup.save_mappings("conn", [{"name": "map", "bank_account": "", "enabled": 1}])


def test_saved_disabled_mapping_can_be_reenabled(setup, flow):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed("Wise Account Map", "map", connection="conn", available=1, enabled=0, bank_account="bank")
    setup.save_mappings("conn", [{"name": "map", "bank_account": "bank", "enabled": 1}])
    assert flow.db.rows["Wise Account Map", "map"]["enabled"] == 1
    assert flow.db.rows["Wise Account Map", "map"]["bank_account"] == "bank"


def test_start_requires_selected_accounts(setup, flow):
    with pytest.raises(ValueError, match="at least one"):
        setup.start("conn")


def test_start_enables_then_queues(setup, flow, monkeypatch):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed("Wise Account Map", "map", connection="conn", available=1, enabled=1, bank_account="bank")
    queued = []
    monkeypatch.setattr(setup, "enqueue", queued.append)
    setup.start("conn")
    assert queued == ["conn"]
    assert flow.db.rows["Wise Connection", "conn"]["enabled"] == 1


def test_setup_requires_system_manager(setup, flow):
    flow.roles.clear()
    with pytest.raises(ValueError, match="Not permitted"):
        setup.state("conn")


def test_navigation_merge_preserves_custom_layout():
    from wise_bank_feed.navigation_data import merge_home_icon

    old = [{"label": "Wise Bank Feed", "idx": 8, "hidden": 1, "in_folder": "Banking"}]
    new = merge_home_icon(old, {"label": "Wise Bank Feed", "hidden": 0, "logo_url": "new"})
    assert new[0]["idx"] == 8 and new[0]["hidden"] == 1 and new[0]["in_folder"] == "Banking"
    assert new[0]["logo_url"] == "new"
    assert "logo_url" not in old[0]
    assert merge_home_icon(new, {"label": "Wise Bank Feed", "logo_url": "new"}) == new


def test_state_never_returns_token(setup, flow):
    flow.db.rows["Wise Connection", "conn"]["api_token"] = "never-return-this"
    result = setup.state("conn")
    assert "api_token" not in result["connection"]
    assert "never-return-this" not in repr(result)


def test_connect_uses_real_client_and_closes_session(setup, flow, monkeypatch):
    import requests

    session = Session([Response([{"id": 12, "type": "business", "details": {"name": "Wharf Ltd"}}])])
    monkeypatch.setattr(requests, "Session", lambda: session)
    flow.seed("Company", "Company A")
    result = setup.connect("Company A", "offline-test-token", "2026-09-01")
    connection = flow.db.rows["Wise Connection", result["connection"]]
    assert connection["company"] == "Company A"
    assert connection["enabled"] == 0
    assert result["profiles"] == [{"id": "12", "label": "Wharf Ltd"}]
    assert "offline-test-token" not in repr(result)
    assert session.closed


def test_bad_token_does_not_create_connection(setup, flow, monkeypatch):
    import requests

    session = Session([Response({}, 401)])
    monkeypatch.setattr(requests, "Session", lambda: session)
    flow.seed("Company", "Company A")
    before = len(flow.rows("Wise Connection"))
    with pytest.raises(WiseError, match="401"):
        setup.connect("Company A", "invalid-test-token", "2026-09-01")
    assert len(flow.rows("Wise Connection")) == before
    assert session.closed


def test_unavailable_account_cannot_be_enabled(setup, flow):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed("Wise Account Map", "map", connection="conn", available=0)
    with pytest.raises(ValueError, match="no longer available"):
        setup.save_mappings("conn", [{"name": "map", "bank_account": "bank"}])


def test_saving_stale_layout_keeps_wise_available(flow, monkeypatch):
    import json
    from types import SimpleNamespace

    monkeypatch.delitem(sys.modules, "wise_bank_feed.navigation", raising=False)
    navigation = importlib.import_module("wise_bank_feed.navigation")
    monkeypatch.setattr(flow.frappe, "get_roles", lambda user=None: ["System Manager"])
    flow.seed("Desktop Icon", "Wise Bank Feed", label="Wise Bank Feed", standard=1, hidden=0)
    doc = SimpleNamespace(user="test@example.invalid", layout=json.dumps([{"label": "Accounting", "idx": 1}]))
    navigation.ensure_layout_icon(doc)
    result = json.loads(doc.layout)
    assert [x["label"] for x in result] == ["Accounting", "Wise Bank Feed"]
    result[-1]["hidden"] = 1
    doc.layout = json.dumps(result)
    navigation.ensure_layout_icon(doc)
    assert json.loads(doc.layout)[-1]["hidden"] == 1
