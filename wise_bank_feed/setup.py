"""Guided setup; credentials never leave Password storage in setup responses."""

import json

import frappe

from .api import connection_doc, discover_accounts
from .client import WiseClient
from .sync import client_for, enqueue

CONNECTION_FIELDS = (
    "name",
    "connection_name",
    "company",
    "environment",
    "profile_id",
    "mode",
    "enabled",
    "start_date",
    "timezone",
    "last_success",
    "status",
)
MAP_FIELDS = (
    "name",
    "account_name",
    "balance_id",
    "currency",
    "balance_type",
    "reported_balance",
    "available",
    "bank_account",
    "enabled",
)


def business_profiles(rows):
    result = []
    for row in rows:
        if str(row.get("type", "")).lower() != "business":
            continue
        identity = WiseClient.ident(row["id"])
        details = row.get("details") or {}
        label = details.get("name") or row.get("businessName") or row.get("name")
        result.append({"id": identity, "label": str(label or f"Business profile {identity}")[:140]})
    return result


@frappe.whitelist(methods=["POST"])
def connections():
    frappe.only_for("System Manager")
    return frappe.get_list("Wise Connection", fields=list(CONNECTION_FIELDS), order_by="modified desc")


@frappe.whitelist(methods=["POST"])
def state(connection):
    c = connection_doc(connection)
    return {
        "connection": {field: c.get(field) for field in CONNECTION_FIELDS},
        "accounts": frappe.get_all(
            "Wise Account Map", filters={"connection": c.name}, fields=list(MAP_FIELDS)
        ),
    }


@frappe.whitelist(methods=["POST"])
def connect(company, token, start_date, timezone="Europe/London", environment="Production"):
    frappe.only_for("System Manager")
    frappe.get_doc("Company", company).check_permission("read")
    with WiseClient(token, environment) as client:
        available = business_profiles(client.profiles())
    if not available:
        frappe.throw("This token has no Wise Business profiles. Use a token from your business account.")
    c = frappe.get_doc(
        dict(
            doctype="Wise Connection",
            connection_name=f"Wise · {company}",
            company=company,
            api_token=token,
            environment=environment,
            start_date=start_date,
            timezone=timezone,
            mode="Activity Review",
            enabled=0,
        )
    ).insert()
    return {"connection": c.name, "profiles": available}


@frappe.whitelist(methods=["POST"])
def profiles(connection):
    c = connection_doc(connection)
    with client_for(c) as client:
        return business_profiles(client.profiles())


@frappe.whitelist(methods=["POST"])
def select_profile(connection, profile_id):
    c = connection_doc(connection)
    if c.enabled:
        frappe.throw("Pause the connection before changing its business profile.")
    # Discovery also verifies token access. Frappe rolls back this save if discovery fails.
    c.profile_id = WiseClient.ident(profile_id)
    c.save()
    discover_accounts(c.name)
    return state(c.name)


@frappe.whitelist(methods=["POST"])
def save_mappings(connection, mappings):
    c = connection_doc(connection)
    if c.enabled:
        frappe.throw("Pause the connection before changing mappings.")
    rows = json.loads(mappings) if isinstance(mappings, str) else mappings
    if not isinstance(rows, list) or len(rows) > 500:
        frappe.throw("Invalid account selection.")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not row.get("name") or row["name"] in seen:
            frappe.throw("Invalid or repeated account selection.")
        seen.add(row["name"])
        m = frappe.get_doc("Wise Account Map", row["name"])
        m.check_permission("write")
        if m.connection != c.name:
            frappe.throw("This account belongs to another connection.")
        bank = row.get("bank_account") or None
        if bank and not m.available:
            frappe.throw("This Wise account is no longer available. Leave it skipped.")
        m.bank_account = bank
        m.enabled = int(bool(bank))
        m.save()  # Existing validation checks currency, company, ledger and booking history.
    return state(c.name)


@frappe.whitelist(methods=["POST"])
def start(connection):
    c = connection_doc(connection)
    mapped = frappe.get_all("Wise Account Map", filters={"connection": c.name}, fields=list(MAP_FIELDS))
    if not any(m["enabled"] and m["available"] and m["bank_account"] for m in mapped):
        frappe.throw("Map at least one available Wise account before starting sync.")
    c.enabled = 1
    c.save()
    enqueue(c.name)
    return state(c.name)


@frappe.whitelist(methods=["POST"])
def pause(connection):
    c = connection_doc(connection)
    c.enabled = 0
    c.save()
    return state(c.name)
