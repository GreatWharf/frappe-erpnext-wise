import importlib
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from wise_bank_feed.navigation_data import desktop_icon_document, merge_home_icon, workspace_sidebar_document


@pytest.fixture
def navigation_module(monkeypatch):
    fake = ModuleType("frappe")
    fake.__version__ = "16.0.0"
    documents = {}
    inserted = []
    cache_keys = []

    def exists(doctype, name):
        return (doctype, name) in documents

    def get_doc(*args):
        if len(args) == 1:
            value = args[0]
            assert isinstance(value, dict)

            def insert(**kwargs):
                inserted.append(value)
                documents[value["doctype"], value["name"]] = value

            return SimpleNamespace(insert=insert)
        doctype, name = args
        record = documents.get((doctype, name), {})
        return SimpleNamespace(as_dict=lambda: dict(record), get=record.get)

    fake.db = SimpleNamespace(exists=exists)
    fake.get_doc = get_doc
    fake.cache = SimpleNamespace(delete_key=cache_keys.append)
    fake.get_roles = lambda user=None: ["System Manager"]
    fake.get_all = lambda doctype, **kwargs: []
    monkeypatch.setitem(sys.modules, "frappe", fake)
    monkeypatch.delitem(sys.modules, "wise_bank_feed.navigation", raising=False)
    module = importlib.import_module("wise_bank_feed.navigation")
    yield module, fake, documents, inserted, cache_keys
    sys.modules.pop("wise_bank_feed.navigation", None)


def test_ensure_navigation_creates_sidebar_and_icon_without_filesystem(navigation_module):
    module, fake, _, inserted, cache_keys = navigation_module
    # No frappe.get_app_path is provided: navigation must build Workspace Sidebar
    # and Desktop Icon documents from static Python data, never the filesystem.
    module.ensure_navigation()
    assert [row["doctype"] for row in inserted] == ["Workspace Sidebar", "Desktop Icon"]
    assert inserted[0] == workspace_sidebar_document()
    assert inserted[1] == desktop_icon_document()
    assert "desktop_icons" in cache_keys
    assert "bootinfo" in cache_keys


def test_ensure_navigation_is_idempotent_and_preserves_customizations(navigation_module):
    module, fake, documents, inserted, _ = navigation_module
    module.ensure_navigation()
    inserted.clear()
    module.ensure_navigation()
    assert inserted == []


def test_ensure_navigation_adds_missing_sidebar_links(navigation_module):
    module, fake, documents, inserted, _ = navigation_module
    module.ensure_navigation()
    banking_items = []

    class Sidebar:
        def __init__(self):
            self.items = banking_items
            self.saved = False

        def append(self, fieldname, item):
            assert fieldname == "items"
            banking_items.append(SimpleNamespace(**item))

        def save(self, **kwargs):
            self.saved = True

    documents["Workspace Sidebar", "Banking"] = {"doctype": "Workspace Sidebar", "name": "Banking"}
    sidebar = Sidebar()
    create_doc = fake.get_doc
    fake.get_doc = lambda *args: sidebar if args == ("Workspace Sidebar", "Banking") else create_doc(*args)
    module.ensure_navigation()
    assert any(getattr(row, "link_to", None) == "wise-setup" for row in banking_items)
    assert any(getattr(row, "url", None) == "/banking" for row in banking_items)


def test_workspace_sidebar_document_matches_json_fixture():
    """navigation_data must stay byte-for-byte consistent with the on-disk fixture."""
    fixture_path = Path(__file__).parents[1] / "wise_bank_feed" / "workspace_sidebar" / "wise_bank_feed.json"
    with fixture_path.open() as source:
        fixture = json.load(source)
    assert workspace_sidebar_document() == fixture


def test_desktop_icon_document_matches_json_fixture():
    """navigation_data must stay byte-for-byte consistent with the on-disk fixture."""
    fixture_path = Path(__file__).parents[1] / "wise_bank_feed" / "desktop_icon" / "wise_bank_feed.json"
    with fixture_path.open() as source:
        fixture = json.load(source)
    assert desktop_icon_document() == fixture


def test_navigation_data_builders_return_independent_copies():
    """Callers may mutate the returned document without corrupting later calls."""
    first = workspace_sidebar_document()
    first["items"].append({"type": "Link"})
    assert workspace_sidebar_document() != first
    icon = desktop_icon_document()
    icon["roles"].append({"role": "Accounts User"})
    assert desktop_icon_document() != icon


def test_apps_screen_permissions_are_explicit_booleans(navigation_module):
    module, fake, *_ = navigation_module
    assert module.has_app_permission() is True
    fake.get_roles = lambda user=None: ["Accounts User"]
    assert module.has_app_permission() is False


def test_ensure_layout_icon_merges_saved_layout(navigation_module):
    module, fake, documents, inserted, _ = navigation_module
    module.ensure_navigation()

    class LayoutDoc:
        def __init__(self, user, layout):
            self.user = user
            self.layout = layout

    doc = LayoutDoc("someone@example.invalid", json.dumps([{"label": "Accounting", "idx": 4, "hidden": 0}]))
    module.ensure_layout_icon(doc)
    updated = json.loads(doc.layout)
    assert any(item["label"] == "Wise Bank Feed" for item in updated)


def test_ensure_layout_icon_skips_non_system_managers(navigation_module):
    module, fake, documents, inserted, _ = navigation_module
    module.ensure_navigation()
    fake.get_roles = lambda user=None: ["Accounts User"]

    class LayoutDoc:
        def __init__(self, user, layout):
            self.user = user
            self.layout = layout

    doc = LayoutDoc("someone@example.invalid", json.dumps([]))
    module.ensure_layout_icon(doc)
    assert doc.layout == "[]"


def test_adds_missing_icon_without_changing_saved_layout():
    layout = [{"label": "Accounting", "idx": 4, "hidden": 0}]
    icon = {"label": "Wise Bank Feed", "logo_url": "/new.svg", "idx": 0}
    result = merge_home_icon(layout, icon)
    assert result[0] == layout[0]
    assert len(layout) == 1
    assert result[1]["idx"] == 5
    assert result[1]["label"] == "Wise Bank Feed"


def test_refreshes_branding_but_preserves_user_placement_and_visibility():
    layout = [
        {
            "label": "Wise Bank Feed",
            "idx": 7,
            "hidden": 1,
            "parent_icon": "Accounting",
            "logo_url": "/old.svg",
        }
    ]
    icon = {"label": "Wise Bank Feed", "logo_url": "/new.svg", "idx": 0, "hidden": 0, "parent_icon": None}
    result = merge_home_icon(layout, icon)
    assert len(result) == 1
    assert result[0]["logo_url"] == "/new.svg"
    assert result[0]["hidden"] == 1
    assert result[0]["idx"] == 7
    assert result[0]["parent_icon"] == "Accounting"
    assert merge_home_icon(result, icon) == result
