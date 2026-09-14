"""Boundary doubles: real connector code, offline HTTP and transactional document storage.

This does not emulate Frappe permissions, MariaDB locking or ERPNext reconciliation.
Those remain staging checks. Copies on read ensure rollback assertions inspect persisted state.
"""

import copy
import importlib
import sys
from contextlib import nullcontext
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest


class Fields(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


@pytest.fixture
def flow(monkeypatch):
    class Store:
        def __init__(self):
            self.rows = {}
            self.committed = {}
            self.sequence = 0

        def matches(self, kind, filters):
            return [
                v
                for (t, _), v in self.rows.items()
                if t == kind and all(v.get(k) == x for k, x in filters.items())
            ]

        def get_value(self, kind, filters, field="name"):
            rows = (
                self.matches(kind, filters)
                if isinstance(filters, dict)
                else [self.rows.get((kind, filters), {})]
            )
            return rows[0].get(field) if rows else None

        def exists(self, kind, filters):
            return self.get_value(kind, filters)

        def set_value(self, kind, name, field, value):
            self.rows[kind, name][field] = value

        def commit(self):
            self.committed = copy.deepcopy(self.rows)

        def rollback(self):
            self.rows = copy.deepcopy(self.committed)

        def sql(self, *args):
            pass  # Locking itself requires a real MariaDB concurrency test.

    db = Store()

    class Doc(Fields):
        def __init__(self, values):
            super().__init__(copy.deepcopy(values))
            object.__setattr__(self, "flags", Fields())
            object.__setattr__(self, "_old", copy.deepcopy(db.rows.get((self.doctype, self.name))))

        def is_new(self):
            return self._old is None

        def get_doc_before_save(self):
            return Fields(self._old) if self._old is not None else None

        def has_value_changed(self, field):
            return (self._old or {}).get(field) != self.get(field)

        def get_password(self, field):
            return "offline-test-token"

        def as_dict(self):
            return dict(self)

        def check_permission(self, permission):
            fake.only_for("System Manager")

        def reload(self):
            values = copy.deepcopy(db.rows[self.doctype, self.name])
            self.clear()
            self.update(values)
            return self

        def insert(self, **kwargs):
            for field in ("source_key", "revision_key", "custom_wise_key"):
                if self.get(field) and db.exists(self.doctype, {field: self[field]}):
                    raise ValueError("Duplicate identity")
            db.sequence += 1
            self.name = self.name or f"row-{db.sequence}"
            return self.save()

        def save(self, **kwargs):
            db.rows[self.doctype, self.name] = copy.deepcopy(dict(self))
            return self

        def submit(self):
            self.docstatus = 1
            return self.save()

    def get_doc(kind, name=None):
        return Doc(kind if isinstance(kind, dict) else db.rows[kind, name])

    def get_all(kind, filters=None, pluck=None, fields=None):
        rows = db.matches(kind, filters or {})
        return [r.get(pluck) for r in rows] if pluck else [{f: r.get(f) for f in fields} for r in rows]

    def throw(message):
        raise ValueError(message)

    def getdate(value=None):
        return date.fromisoformat(str(value)[:10]) if value else date(2026, 9, 14)

    utils = SimpleNamespace(
        now_datetime=lambda: datetime(2026, 9, 14, 12),
        get_datetime=lambda x: datetime.fromisoformat(str(x)),
        getdate=getdate,
        today=lambda: "2026-09-14",
        cint=lambda x: int(x or 0),
    )
    roles = ["System Manager"]
    fake = SimpleNamespace(
        db=db,
        get_doc=get_doc,
        get_all=get_all,
        utils=utils,
        throw=throw,
        session=SimpleNamespace(user="test@example.invalid"),
        get_roles=lambda: roles,
        only_for=lambda role: None if role in roles else throw("Not permitted"),
        whitelist=lambda **kwargs: lambda f: f,
        cache=SimpleNamespace(lock=lambda *a, **kw: nullcontext()),
    )
    monkeypatch.setitem(sys.modules, "frappe", fake)
    monkeypatch.setitem(sys.modules, "frappe.utils", utils)
    monkeypatch.setitem(sys.modules, "frappe.model", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "frappe.model.document", SimpleNamespace(Document=Doc))
    modules = {}
    for name in ("documents", "importer", "sync", "api"):
        full = "wise_bank_feed." + name
        monkeypatch.delitem(sys.modules, full, raising=False)
        modules[name] = importlib.import_module(full)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(modules["sync"], "datetime", Clock)

    def seed(kind, name, **values):
        return get_doc(dict(doctype=kind, name=name, **values)).save()

    seed(
        "Wise Connection",
        "conn",
        company="Company A",
        environment="Production",
        profile_id="123",
        mode="Activity Review",
        enabled=1,
        timezone="Europe/London",
        start_date="2026-09-01",
    )
    seed("Bank Account", "bank", is_company_account=1, company="Company A", account="ledger")
    seed("Account", "ledger", company="Company A", account_currency="GBP", account_type="Bank")
    db.commit()
    return SimpleNamespace(
        **modules, db=db, frappe=fake, seed=seed, roles=roles, Doc=Doc, rows=lambda kind: db.matches(kind, {})
    )
