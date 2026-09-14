from decimal import Decimal

import pytest

from wise_bank_feed.core import activity_identity, amount, key, statement_entry, validate_mapping


def test_identity_is_scoped_and_stable():
    assert key("production", "123", "a") == key("production", "123", "a")
    assert key("production", "123", "a") != key("sandbox", "123", "a")
    assert key("ab", "c") != key("a", "bc")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "", None, True, "1,000"])
def test_bad_money(value):
    with pytest.raises(ValueError):
        amount(value)


def test_money_precise():
    assert amount("0.10") + amount("0.20") == Decimal("0.30")


def test_mapping():
    bank = dict(is_company_account=1, company="A", account="GL")
    ledger = dict(company="A", account_currency="GBP", is_group=0, account_type="Bank", disabled=0)
    validate_mapping("A", "GBP", bank, ledger)
    for changed in [dict(company="B"), dict(account_currency="USD"), dict(is_group=1), dict(disabled=1)]:
        with pytest.raises(ValueError):
            validate_mapping("A", "GBP", bank, ledger | changed)


def test_statement():
    row = dict(
        referenceNumber="CARD-123",
        type="DEBIT",
        date="2026-09-01T01:00:00Z",
        amount=dict(value="-12.40", currency="GBP"),
    )
    result = statement_entry(row, "GBP", "Europe/London")
    assert result["withdrawal"] == Decimal("12.40")
    assert result["deposit"] == 0
    assert result["date"] == "2026-09-01"
    with pytest.raises(ValueError):
        statement_entry(row, "USD", "UTC")
    with pytest.raises(ValueError):
        statement_entry(row | {"referenceNumber": ""}, "GBP", "UTC")
    with pytest.raises(ValueError):
        statement_entry(row | {"type": "PENDING"}, "GBP", "UTC")


def test_activity_identity_prefers_resource():
    a = {"id": "display1", "resource": {"id": 42, "type": "TRANSFER"}}
    b = a | {"id": "display2"}
    assert activity_identity(a) == activity_identity(b)
    assert activity_identity({"id": "a"}) != activity_identity({"id": "b"})
