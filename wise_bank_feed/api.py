import json
from decimal import Decimal

import frappe
from frappe.utils import getdate, today

from .core import amount, key
from .documents import lock_connection
from .importer import bank_entry, save
from .sync import client_for, discover, enqueue


def has_permission():
    return "System Manager" in frappe.get_roles()


def connection_doc(name):
    frappe.only_for("System Manager")
    lock_connection(name)
    c = frappe.get_doc("Wise Connection", name)
    c.check_permission("write")
    return c


@frappe.whitelist(methods=["POST"])
def profiles(connection):
    c = connection_doc(connection)
    with client_for(c) as client:
        return [
            {"id": p["id"], "type": p.get("type")}
            for p in client.profiles()
            if str(p.get("type", "")).lower() == "business"
        ]


@frappe.whitelist(methods=["POST"])
def discover_accounts(connection):
    c = connection_doc(connection)
    if c.enabled:
        frappe.throw("Pause before discovering or editing mappings.")
    if not c.profile_id:
        frappe.throw("Discover and select a Business profile first.")
    with client_for(c) as client:
        if not any(
            str(p["id"]) == c.profile_id and str(p.get("type", "")).lower() == "business"
            for p in client.profiles()
        ):
            frappe.throw("This token does not expose the selected Business profile.")
        discover(c, client)
    return frappe.get_all(
        "Wise Account Map",
        filters={"connection": c.name},
        fields=[
            "name",
            "account_name",
            "balance_id",
            "currency",
            "balance_type",
            "investment_state",
            "reported_balance",
            "available",
            "bank_account",
            "enabled",
        ],
    )


@frappe.whitelist(methods=["POST"])
def sync_now(connection):
    c = connection_doc(connection)
    if not c.enabled:
        frappe.throw("Enable the connection before synchronizing.")
    enqueue(c.name)
    return "Queued"


@frappe.whitelist(methods=["POST"])
def create_reviewed_booking(
    activity, account_map, direction, value, booking_date, evidence, expected_hash, confirmed=0
):
    frappe.only_for("System Manager")
    activity_doc = frappe.get_doc("Wise Activity", activity)
    c = connection_doc(activity_doc.connection)
    activity_doc.reload()
    if activity_doc.payload_hash != expected_hash:
        frappe.throw("Source changed since you opened it. Reload and review again.")
    if c.mode != "Activity Review":
        frappe.throw("Manual activity booking is only available in Activity Review mode.")
    if activity_doc.upstream_status != "COMPLETED":
        frappe.throw("Only completed activities can be booked.")
    if not frappe.utils.cint(confirmed) or not str(evidence or "").strip():
        frappe.throw("Confirm the exact booked details and record your evidence.")
    m = frappe.get_doc("Wise Account Map", account_map)
    if m.connection != c.name or not m.enabled or not m.available or not m.bank_account:
        frappe.throw("Select an enabled mapped account from this connection.")
    money = amount(value)
    if money <= 0 or direction not in ("Deposit", "Withdrawal"):
        frappe.throw("Use a positive booked amount and direction.")
    if not booking_date:
        frappe.throw("Confirm the booked date from Wise.")
    if getdate(booking_date) > getdate(today()):
        frappe.throw("Booking date cannot be in the future.")
    identity = key(c.environment, c.profile_id, m.balance_id, "reviewed", activity_doc.source_key, direction)
    entry = dict(
        reference="WA-" + activity_doc.source_key,
        date=str(getdate(booking_date)),
        deposit=money if direction == "Deposit" else Decimal(0),
        withdrawal=money if direction == "Withdrawal" else Decimal(0),
    )
    existing = frappe.db.get_value("Wise Booking", {"source_key": identity}, "name")
    if existing:
        frappe.throw(
            "A booking already exists for this activity, account and direction. Open its review record."
        )
    result = bank_entry(c, m, identity, entry, json.loads(activity_doc.payload), activity_doc.name, evidence)
    # Multiple account legs can still be required, e.g. FX. Completion is a separate explicit action.
    return result.bank_transaction


@frappe.whitelist(methods=["POST"])
def finish_review(activity, note, expected_hash):
    doc = frappe.get_doc("Wise Activity", activity)
    connection_doc(doc.connection)
    doc.reload()
    if doc.payload_hash != expected_hash:
        frappe.throw("Source changed. Reload before finishing review.")
    if not str(note or "").strip():
        frappe.throw("Record the review outcome, including any omitted or non-monetary activity.")
    if frappe.db.exists("Wise Booking", {"activity": doc.name, "needs_review": 1}):
        frappe.throw("Resolve changed booking reviews first.")
    doc.needs_review = 0
    doc.review_note = f"{frappe.session.user}: {note}"
    save(doc)


@frappe.whitelist(methods=["POST"])
def acknowledge_change(booking, note, expected_hash):
    doc = frappe.get_doc("Wise Booking", booking)
    connection_doc(doc.connection)
    doc.reload()
    if (doc.latest_hash or doc.source_hash) != expected_hash:
        frappe.throw("Source changed. Reload before acknowledging.")
    if not str(note or "").strip():
        frappe.throw("Record how the discrepancy and reconciliations were resolved.")
    doc.needs_review = 0
    doc.review_note = f"{frappe.session.user}: {note}"
    save(doc)
    frappe.db.set_value("Bank Transaction", doc.bank_transaction, "custom_wise_review", 0)
