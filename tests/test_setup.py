import importlib
import sys

import pytest


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


def test_unmapped_accounts_are_disabled(setup, flow):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed("Wise Account Map", "map", connection="conn", available=1, enabled=1, bank_account="bank")
    setup.save_mappings("conn", [{"name": "map", "bank_account": ""}])
    assert flow.db.rows["Wise Account Map", "map"]["enabled"] == 0
    assert not flow.db.rows["Wise Account Map", "map"]["bank_account"]


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


def test_bad_token_does_not_create_connection(setup, flow, monkeypatch):
    class BadClient:
        def __init__(self, *args):
            pass

        def __enter__(self):
            raise ValueError("Wise HTTP 401")

        def __exit__(self, *args):
            pass

    flow.seed("Company", "Company A")
    monkeypatch.setattr(setup, "WiseClient", BadClient)
    before = len(flow.rows("Wise Connection"))
    with pytest.raises(ValueError, match="401"):
        setup.connect("Company A", "invalid-token", "2026-09-01")
    assert len(flow.rows("Wise Connection")) == before


def test_unavailable_account_cannot_be_enabled(setup, flow):
    flow.db.rows["Wise Connection", "conn"]["enabled"] = 0
    flow.seed("Wise Account Map", "map", connection="conn", available=0)
    with pytest.raises(ValueError, match="no longer available"):
        setup.save_mappings("conn", [{"name": "map", "bank_account": "bank"}])
