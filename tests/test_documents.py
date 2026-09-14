import pytest


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile_id", "999"),
        ("company", "Other"),
        ("environment", "Sandbox"),
        ("mode", "Statements"),
        ("start_date", "2026-01-01"),
        ("timezone", "UTC"),
    ],
)
def test_source_identity_cannot_change_after_discovery(flow, field, value):
    flow.seed("Wise Account Map", "map", connection="conn")
    c = flow.documents.Connection(flow.db.rows["Wise Connection", "conn"])
    c[field] = value
    with pytest.raises(ValueError, match="immutable"):
        c.validate()


def test_active_connection_cannot_change_mapping(flow):
    flow.seed("Wise Account Map", "map", connection="conn", bank_account=None, enabled=0)
    doc = flow.documents.AccountMap(flow.db.rows["Wise Account Map", "map"])
    with pytest.raises(ValueError, match="Pause"):
        doc.validate()


def test_unmapped_account_can_remain_disabled(flow):
    flow.db.set_value("Wise Connection", "conn", "enabled", 0)
    flow.seed("Wise Account Map", "map", connection="conn", bank_account=None, enabled=0)
    doc = flow.documents.AccountMap(flow.db.rows["Wise Account Map", "map"])
    doc.validate()
    doc.enabled = 1
    with pytest.raises(ValueError, match="Bank Account"):
        doc.validate()


def test_wrong_company_mapping_is_rejected(flow):
    flow.db.set_value("Wise Connection", "conn", "enabled", 0)
    flow.db.set_value("Bank Account", "bank", "company", "Other")
    doc = flow.documents.AccountMap(
        dict(
            doctype="Wise Account Map",
            name="map",
            connection="conn",
            bank_account="bank",
            currency="GBP",
            enabled=1,
        )
    )
    with pytest.raises(ValueError, match="company Bank Account"):
        doc.validate()


def test_managed_audit_record_cannot_be_edited_directly(flow):
    doc = flow.documents.ManagedDocument(dict(doctype="Wise Activity", name="activity"))
    with pytest.raises(ValueError, match="managed"):
        doc.validate()
