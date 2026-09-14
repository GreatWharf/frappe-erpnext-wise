import importlib
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest


@pytest.fixture
def guards(monkeypatch):
    def throw(message):
        raise ValueError(message)

    monkeypatch.setitem(sys.modules, "frappe", SimpleNamespace(throw=throw))
    sys.modules.pop("wise_bank_feed.guards", None)
    return importlib.import_module("wise_bank_feed.guards")


class Doc:
    def __init__(self, current, previous):
        self.current, self.previous = current, previous
        self.flags = SimpleNamespace(wise_import=False)

    def get(self, k):
        return self.current.get(k)

    def get_doc_before_save(self):
        return self.previous

    def has_value_changed(self, k):
        a, b = self.previous.get(k), self.current.get(k)
        if isinstance(a, date) and isinstance(b, str):
            b = date.fromisoformat(b)
        return a != b

    def is_child_table_same(self, k):
        # Distinct document instances with identical logical contents.
        return [vars(x) for x in self.previous[k]] == [vars(x) for x in self.current[k]]


def test_dates_decimals_and_unchanged_child_rows(guards):
    old = {
        "custom_wise_key": "key",
        "custom_wise_review": 1,
        "date": date(2026, 9, 1),
        "deposit": 0.1,
        "withdrawal": 0,
        "payment_entries": [SimpleNamespace(payment_document="Sales Invoice", allocated_amount=0.1)],
    }
    current = old | {
        "date": "2026-09-01",
        "deposit": Decimal("0.1"),
        "payment_entries": [SimpleNamespace(payment_document="Sales Invoice", allocated_amount=0.1)],
    }
    guards.validate(Doc(current, old))
    with pytest.raises(ValueError):
        guards.validate(Doc(current | {"deposit": Decimal("0.2")}, old))
    with pytest.raises(ValueError):
        guards.validate(Doc(current | {"payment_entries": []}, old))


def test_cannot_attach_provenance_to_existing_nonwise(guards):
    with pytest.raises(ValueError, match="only be assigned"):
        guards.validate(Doc({"custom_wise_key": "fake"}, {"name": "old"}))
