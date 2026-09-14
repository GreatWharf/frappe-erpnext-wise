"""Bounded jobs; all data and checkpoints commit together. Failures roll back the whole job."""

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import frappe

from .client import WiseClient, WiseError
from .core import activity_identity, fingerprint, key, statement_entry
from .documents import lock_connection
from .importer import bank_entry, hold, new, revise, save


def utc(value):
    dt = frappe.utils.get_datetime(value)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat()


@contextmanager
def client_for(c):
    client = WiseClient(c.get_password("api_token"), c.environment)
    try:
        yield client
    finally:
        client.close()


def discover(c, client):
    rows = client.balances(c.profile_id)
    seen = set()
    for row in rows:
        bid = client.ident(row["id"])
        currency = str(row["currency"])
        if len(currency) != 3 or not currency.isupper():
            raise ValueError("Invalid Wise currency.")
        source_key = key(c.environment, c.profile_id, bid)
        name = frappe.db.get_value("Wise Account Map", {"source_key": source_key}, "name")
        values = dict(
            account_name=str(row.get("name") or "Main balance")[:140],
            balance_type=row.get("type"),
            investment_state=row.get("investmentState"),
            reported_balance=str((row.get("amount") or {}).get("value", "")),
            available=1,
        )
        if name:
            doc = frappe.get_doc("Wise Account Map", name)
            if doc.connection != c.name:
                frappe.throw("This Wise account is already owned by another connection.")
            if doc.currency != currency:
                frappe.throw("Wise account currency changed; review mapping.")
            doc.update(values)
            save(doc)
        else:
            doc = new(
                "Wise Account Map",
                connection=c.name,
                balance_id=bid,
                currency=currency,
                source_key=source_key,
                enabled=0,
                **values,
            )
        seen.add(doc.name)
    for name in frappe.get_all("Wise Account Map", filters={"connection": c.name}, pluck="name"):
        if name not in seen:
            frappe.db.set_value("Wise Account Map", name, "available", 0)


def ingest_activity(c, row):
    source_key = key(c.environment, c.profile_id, activity_identity(row))
    digest = fingerprint(row)
    name = frappe.db.get_value("Wise Activity", {"source_key": source_key}, "name")
    values = dict(
        upstream_id=str(row["id"]),
        activity_type=str(row.get("type", ""))[:140],
        upstream_status=str(row.get("status", ""))[:140],
        primary_amount=str(row.get("primaryAmount", ""))[:140],
        secondary_amount=str(row.get("secondaryAmount", ""))[:140],
        payload=json.dumps(row, default=str),
        payload_hash=digest,
        last_seen=frappe.utils.now_datetime(),
    )
    if not name:
        return new("Wise Activity", connection=c.name, source_key=source_key, needs_review=1, **values)
    doc = frappe.get_doc("Wise Activity", name)
    if doc.payload_hash != digest:
        revise(c, doc, json.loads(doc.payload))
        doc.needs_review = 1
        for booking in frappe.get_all("Wise Booking", filters={"activity": name}, pluck="name"):
            book = frappe.get_doc("Wise Booking", booking)
            book.latest_hash = digest
            revise(c, book, row)
            hold(book)
    doc.update(values)
    return save(doc)


def enqueue(name):
    return frappe.enqueue(
        "wise_bank_feed.sync.run",
        connection=name,
        queue="long",
        timeout=900,
        job_id="wise-sync-" + name,
        deduplicate=True,
        enqueue_after_commit=True,
    )


def schedule():
    for name in frappe.get_all("Wise Connection", filters={"enabled": 1}, pluck="name"):
        enqueue(name)


def run(connection):
    with frappe.cache.lock("wise-feed:" + connection, timeout=1000, blocking_timeout=1):
        lock_connection(connection)
        c = frappe.get_doc("Wise Connection", connection)
        if not c.enabled:
            return
        try:
            with client_for(c) as client:
                discover(c, client)
                now = datetime.now(timezone.utc)
                count, bookings = 0, 0
                if c.mode == "Activity Review":
                    cursor = utc(c.cursor_at or c.start_date)
                    end = min(now, cursor + timedelta(days=7))
                    start = max(utc(c.start_date), cursor - timedelta(days=7))
                    for row in client.activities(c.profile_id, stamp(start), stamp(end)):
                        ingest_activity(c, row)
                        count += 1
                    c.cursor_at = end.replace(tzinfo=None)
                    # since/until are not documented as updated timestamps. Audit older activity too.
                    if end >= now and (not c.audit_at or now - utc(c.audit_at) >= timedelta(days=7)):
                        for row in client.activities(
                            c.profile_id, stamp(max(utc(c.start_date), now - timedelta(days=90))), stamp(now)
                        ):
                            ingest_activity(c, row)
                            count += 1
                        c.audit_at = now.replace(tzinfo=None)
                else:
                    maps = frappe.get_all(
                        "Wise Account Map",
                        filters={"connection": c.name, "enabled": 1, "available": 1},
                        pluck="name",
                    )
                    if not maps:
                        raise ValueError("Enable at least one mapped account for statement sync.")
                    for name in maps:
                        m = frappe.get_doc("Wise Account Map", name)
                        if not m.bank_account:
                            raise ValueError("Enabled mapping has no Bank Account.")
                        cursor = utc(m.cursor_at or c.start_date)
                        end = min(now, cursor + timedelta(days=7))
                        start = max(utc(c.start_date), cursor - timedelta(days=7))
                        rows = client.statement(
                            c.profile_id, m.balance_id, m.currency, stamp(start), stamp(end)
                        )
                        references = set()
                        for row in rows:
                            entry = statement_entry(row, m.currency, c.timezone)
                            if entry["reference"] in references:
                                raise ValueError("Repeated statement reference; checkpoint not advanced.")
                            references.add(entry["reference"])
                            identity = key(
                                c.environment, c.profile_id, m.balance_id, "statement", entry["reference"]
                            )
                            bank_entry(c, m, identity, entry, row)
                            bookings += 1
                        m.cursor_at = end.replace(tzinfo=None)
                        save(m)
                c.last_success = now.replace(tzinfo=None)
                c.status = (
                    "Activities synced; review booked details before creating Bank Transactions."
                    if c.mode == "Activity Review"
                    else "Statement sync completed."
                )
                save(c)
                new(
                    "Wise Sync Log",
                    connection=c.name,
                    result="Success",
                    message=c.status,
                    activities=count,
                    bookings=bookings,
                )
                frappe.db.commit()
        except Exception as exc:
            frappe.db.rollback()
            # No traceback/local variables/token or raw response in the audit log.
            message = (
                str(exc)
                if isinstance(exc, WiseError)
                else "Sync failed (" + type(exc).__name__ + "). Check mappings, dates and schema."
            )
            frappe.db.set_value("Wise Connection", connection, "status", message)
            new("Wise Sync Log", connection=connection, result="Error", message=message)
            frappe.db.commit()
