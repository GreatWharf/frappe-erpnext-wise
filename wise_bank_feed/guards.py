import frappe

from .core import amount


def validate(doc, method=None):
    old = doc.get_doc_before_save()
    if (
        doc.get("custom_wise_key")
        and (not old or not old.get("custom_wise_key"))
        and not doc.flags.wise_import
    ):
        frappe.throw("Wise source keys can only be assigned by the connector.")
    if old and old.get("custom_wise_key"):
        for field in (
            "custom_wise_key",
            "custom_wise_review",
            "bank_account",
            "company",
            "currency",
            "date",
            "deposit",
            "withdrawal",
            "transaction_id",
        ):
            changed = (
                (amount(old.get(field) or 0) != amount(doc.get(field) or 0))
                if field in ("deposit", "withdrawal")
                else doc.has_value_changed(field)
            )
            if changed:
                frappe.throw("Wise booking fields are immutable. Review source changes separately.")
        if doc.get("custom_wise_review") and not doc.is_child_table_same("payment_entries"):
            frappe.throw("Resolve the Wise source review before changing reconciliation allocations.")


def before_cancel(doc, method=None):
    if doc.get("custom_wise_key"):
        frappe.only_for("System Manager")
        frappe.throw(
            "Resolve the source booking through Wise review before cancelling externally imported entries."
        )


def before_delete(doc, method=None):
    if doc.get("custom_wise_key"):
        frappe.throw("Retain Wise Bank Transactions to preserve duplicate prevention and audit history.")
