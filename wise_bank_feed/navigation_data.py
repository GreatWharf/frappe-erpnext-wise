from copy import deepcopy


def workspace_sidebar_document():
    """v16 Workspace Sidebar entry point, kept in sync with workspace_sidebar/wise_bank_feed.json."""
    return {
        "doctype": "Workspace Sidebar",
        "name": "Wise Bank Feed",
        "title": "Wise Bank Feed",
        "app": "wise_bank_feed",
        "module": "Wise Bank Feed",
        "standard": 1,
        "header_icon": "landmark",
        "items": [
            {
                "type": "Link",
                "label": "Connect Wise",
                "link_type": "Page",
                "link_to": "wise-setup",
                "icon": "plug",
                "child": 0,
            },
            {
                "type": "Link",
                "label": "Activity inbox",
                "link_type": "DocType",
                "link_to": "Wise Activity",
                "icon": "list",
                "child": 0,
            },
            {
                "type": "Link",
                "label": "Banking app",
                "link_type": "URL",
                "url": "/banking",
                "icon": "landmark",
                "child": 0,
            },
            {
                "type": "Link",
                "label": "Bank transactions",
                "link_type": "DocType",
                "link_to": "Bank Transaction",
                "icon": "arrow-left-right",
                "child": 0,
            },
            {
                "type": "Link",
                "label": "Account mappings",
                "link_type": "DocType",
                "link_to": "Wise Account Map",
                "icon": "link",
                "child": 0,
            },
            {
                "type": "Link",
                "label": "Sync logs",
                "link_type": "DocType",
                "link_to": "Wise Sync Log",
                "icon": "list",
                "child": 0,
            },
            {
                "type": "Link",
                "label": "Connection settings",
                "link_type": "DocType",
                "link_to": "Wise Connection",
                "icon": "settings",
                "child": 0,
            },
        ],
    }


def desktop_icon_document():
    """v16 Desktop Icon entry point, kept in sync with desktop_icon/wise_bank_feed.json."""
    return {
        "doctype": "Desktop Icon",
        "name": "Wise Bank Feed",
        "label": "Wise Bank Feed",
        "icon_type": "App",
        "link_type": "External",
        "link": "/desk/wise-setup?sidebar=Wise%20Bank%20Feed",
        "app": "wise_bank_feed",
        "standard": 1,
        "hidden": 0,
        "logo_url": "/assets/wise_bank_feed/images/wise-icon.png",
        "roles": [{"role": "System Manager"}],
    }


def merge_home_icon(layout, icon):
    """Refresh app metadata while retaining the user's layout and hidden state."""
    result = deepcopy(layout)
    for item in result:
        if item.get("label") == icon["label"]:
            placement = {
                key: item[key] for key in ("idx", "hidden", "parent_icon", "in_folder") if key in item
            }
            item.update(icon)
            item.update(placement)
            return result
    added = deepcopy(icon)
    added["idx"] = max((item.get("idx") or 0 for item in result), default=0) + 1
    result.append(added)
    return result
