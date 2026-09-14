"""Mock persistence tests exercise importer decisions without a live Frappe bench."""

import importlib
import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest


@pytest.fixture
def env(monkeypatch):
    rows = {}
    counter = [0]

    class Doc(SimpleNamespace):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.flags = SimpleNamespace()

        def __getattr__(self, k):
            return None

        def as_dict(self):
            return vars(self)

        def insert(self, **kwargs):
            counter[0] += 1
            self.name = "doc-" + str(counter[0])
            rows[(self.doctype, self.name)] = self
            return self

        def save(self, **kwargs):
            return self

        def submit(self):
            self.docstatus = 1

    def get_doc(t, name=None):
        if isinstance(t, dict):
            return Doc(**t)
        return rows[(t, name)]

    def get_value(t, filters, field):
        return next(
            (
                getattr(d, field)
                for (dt, n), d in rows.items()
                if dt == t and all(getattr(d, k) == v for k, v in filters.items())
            ),
            None,
        )

    def set_value(t, n, f, v):
        setattr(rows[(t, n)], f, v)

    fake = SimpleNamespace(
        get_doc=get_doc,
        db=SimpleNamespace(
            get_value=get_value, exists=lambda t, f: bool(get_value(t, f, "name")), set_value=set_value
        ),
        session=SimpleNamespace(user="Administrator"),
        utils=SimpleNamespace(now_datetime=lambda: "2026-09-14"),
    )

    def throw(message):
        raise ValueError(message)

    fake.throw = throw
    monkeypatch.setitem(sys.modules, "frappe", fake)
    sys.modules.pop("wise_bank_feed.importer", None)
    importer = importlib.import_module("wise_bank_feed.importer")
    rows[("Bank Account", "bank")] = Doc(
        name="bank", doctype="Bank Account", is_company_account=1, company="A", account="GL"
    )
    rows[("Account", "GL")] = Doc(
        name="GL",
        doctype="Account",
        company="A",
        account_currency="GBP",
        account_type="Bank",
        is_group=0,
        disabled=0,
    )
    c = Doc(name="conn", company="A")
    m = Doc(name="map", bank_account="bank", currency="GBP")
    return importer, rows, c, m


def test_repeat_import_creates_one_bank_transaction(env):
    imp, rows, c, m = env
    entry = {"reference": "CARD-1", "date": "2026-09-01", "deposit": Decimal(0), "withdrawal": Decimal("10")}
    first = imp.bank_entry(c, m, "identity", entry, {"value": 10})
    second = imp.bank_entry(c, m, "identity", entry, {"value": 10})
    assert first.name == second.name
    assert len([d for (t, n), d in rows.items() if t == "Bank Transaction"]) == 1
    assert rows[("Bank Transaction", first.bank_transaction)].docstatus == 1


def test_changed_source_holds_original_bank_transaction(env):
    imp, rows, c, m = env
    entry = {"reference": "CARD-1", "date": "2026-09-01", "deposit": Decimal(0), "withdrawal": Decimal("10")}
    first = imp.bank_entry(c, m, "identity", entry, {"value": 10})
    imp.bank_entry(c, m, "identity", entry | {"withdrawal": Decimal("12")}, {"value": 12})
    bank = rows[("Bank Transaction", first.bank_transaction)]
    assert first.needs_review == 1 and bank.custom_wise_review == 1
    assert bank.withdrawal == Decimal("10")
    first.needs_review = 0
    bank.custom_wise_review = 0
    imp.bank_entry(c, m, "identity", entry | {"withdrawal": Decimal("12")}, {"value": 12})
    assert first.needs_review == 0, "Acknowledged identical revision must not reopen forever"


def test_orphan_bank_identity_never_recreated(env):
    imp, rows, c, m = env
    entry = {"reference": "CARD-1", "date": "2026-09-01", "deposit": Decimal(0), "withdrawal": Decimal("10")}
    first = imp.bank_entry(c, m, "identity", entry, {"value": 10})
    del rows[("Wise Booking", first.name)]
    with pytest.raises(ValueError, match="already carries"):
        imp.bank_entry(c, m, "identity", entry, {"value": 10})
