import importlib
import sys
from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("fail", [False, True])
def test_checkpoint_and_transaction_failure(monkeypatch, fail):
    events = []
    c = SimpleNamespace(
        name="conn",
        enabled=1,
        mode="Activity Review",
        cursor_at=None,
        start_date="2026-09-01",
        audit_at=None,
        profile_id="123",
        company="A",
    )
    fake = SimpleNamespace(
        cache=SimpleNamespace(lock=lambda *a, **k: nullcontext()),
        get_doc=lambda *a: c,
        db=SimpleNamespace(
            commit=lambda: events.append("commit"),
            rollback=lambda: events.append("rollback"),
            set_value=lambda *a: events.append("status"),
        ),
    )
    monkeypatch.setitem(sys.modules, "frappe", fake)
    monkeypatch.setitem(
        sys.modules, "wise_bank_feed.documents", SimpleNamespace(lock_connection=lambda n: None)
    )
    monkeypatch.setitem(
        sys.modules,
        "wise_bank_feed.importer",
        SimpleNamespace(
            new=lambda *a, **k: events.append(("log", k.get("result"))),
            save=lambda d: events.append("save"),
            revise=lambda *a: None,
            hold=lambda *a: None,
            bank_entry=lambda *a: None,
        ),
    )
    sys.modules.pop("wise_bank_feed.sync", None)
    sync = importlib.import_module("wise_bank_feed.sync")

    class Client:
        def activities(self, *a):
            yield {"id": "one"}
            if fail:
                raise sync.WiseError("Wise HTTP 429.", 429)

    monkeypatch.setattr(sync, "client_for", lambda c: nullcontext(Client()))
    monkeypatch.setattr(sync, "discover", lambda *a: None)
    monkeypatch.setattr(sync, "ingest_activity", lambda *a: events.append("activity"))
    monkeypatch.setattr(sync, "utc", lambda v: datetime.fromisoformat(v).replace(tzinfo=timezone.utc))
    sync.run("conn")
    if fail:
        assert c.cursor_at is None
        assert events.index("rollback") < events.index(("log", "Error")) < events.index("commit")
    else:
        assert c.cursor_at == datetime(2026, 9, 8)
        assert "rollback" not in events
        assert events[-1] == "commit"
