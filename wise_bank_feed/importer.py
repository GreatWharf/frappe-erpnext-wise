import json

import frappe

from .core import amount, fingerprint, key, validate_mapping


def save(doc):
    doc.flags.wise_internal = True
    return doc.save(ignore_permissions=True)


def new(doctype, **values):
    doc = frappe.get_doc(dict(doctype=doctype, **values))
    doc.flags.wise_internal = True
    return doc.insert(ignore_permissions=True)


def revise(connection, doc, payload):
    digest = fingerprint(payload)
    revision_key = key(doc.doctype, doc.name, digest)
    if not frappe.db.exists("Wise Source Revision", {"revision_key": revision_key}):
        new(
            "Wise Source Revision",
            connection=connection.name,
            source_doctype=doc.doctype,
            source_name=doc.name,
            revision_key=revision_key,
            payload=json.dumps(payload, default=str),
            observed_at=frappe.utils.now_datetime(),
        )


def hold(booking):
    booking.needs_review = 1
    save(booking)
    if booking.bank_transaction:
        frappe.db.set_value("Bank Transaction", booking.bank_transaction, "custom_wise_review", 1)


def bank_entry(connection, mapping, source_key, entry, payload, activity=None, evidence=None):
    bank = frappe.get_doc("Bank Account", mapping.bank_account)
    ledger = frappe.get_doc("Account", bank.account)
    validate_mapping(connection.company, mapping.currency, bank.as_dict(), ledger.as_dict())
    existing = frappe.db.get_value("Wise Booking", {"source_key": source_key}, "name")
    digest = fingerprint(payload)
    if existing:
        doc = frappe.get_doc("Wise Booking", existing)
        if (doc.latest_hash or doc.source_hash) != digest:
            revise(connection, doc, payload)
            doc.latest_hash = digest
            hold(doc)
        return doc
    # Check surviving provenance, including cancelled or manually altered documents.
    if frappe.db.exists("Bank Transaction", {"custom_wise_key": source_key}):
        frappe.throw("A Bank Transaction already carries this Wise identity. Restore its audit record.")
    doc = new(
        "Wise Booking",
        connection=connection.name,
        account_map=mapping.name,
        activity=activity,
        source_key=source_key,
        reference=entry["reference"],
        booking_date=entry["date"],
        deposit=str(entry["deposit"]),
        withdrawal=str(entry["withdrawal"]),
        source_hash=digest,
        payload=json.dumps(payload, default=str),
        confirmed_by=frappe.session.user if activity else None,
        evidence=evidence,
    )
    transaction = frappe.get_doc(
        dict(
            doctype="Bank Transaction",
            bank_account=mapping.bank_account,
            company=connection.company,
            currency=mapping.currency,
            date=entry["date"],
            deposit=entry["deposit"],
            withdrawal=entry["withdrawal"],
            transaction_id=entry["reference"][:140],
            description="Wise "
            + ("reviewed activity" if activity else "statement")
            + "; source "
            + source_key,
            custom_wise_key=source_key,
        )
    )
    transaction.flags.wise_import = True
    transaction.insert(ignore_permissions=True)
    if (
        amount(transaction.deposit) != entry["deposit"]
        or amount(transaction.withdrawal) != entry["withdrawal"]
    ):
        frappe.throw(
            "ERPNext currency precision would round this Wise amount; adjust precision before retrying."
        )
    transaction.submit()
    doc.bank_transaction = transaction.name
    save(doc)
    return doc
