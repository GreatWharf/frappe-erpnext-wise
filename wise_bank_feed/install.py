import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def check_versions():
    import erpnext

    if frappe.__version__.split(".")[0] != "16" or erpnext.__version__.split(".")[0] != "16":
        frappe.throw("Wise Bank Feed requires ERPNext and Frappe v16.")
    if frappe.db.db_type != "mariadb":
        frappe.throw("This release requires MariaDB.")


def after_migrate():
    from .navigation import ensure_navigation

    check_versions()
    ensure_navigation()
    create_custom_fields(
        {
            "Bank Transaction": [
                dict(
                    fieldname="custom_wise_key",
                    label="Wise Source Key",
                    fieldtype="Data",
                    unique=1,
                    read_only=1,
                    no_copy=1,
                    insert_after="transaction_id",
                ),
                dict(
                    fieldname="custom_wise_review",
                    label="Wise Source Changed — Review Required",
                    fieldtype="Check",
                    read_only=1,
                    no_copy=1,
                    allow_on_submit=1,
                    insert_after="custom_wise_key",
                ),
            ]
        },
        update=True,
    )


def before_uninstall():
    if frappe.db.exists("Wise Connection", {"enabled": 1}):
        frappe.throw("Pause Wise connections and drain workers before uninstalling.")
    if frappe.db.exists("Wise Booking", {"needs_review": 1}):
        frappe.throw("Resolve Wise booking reviews before uninstalling.")
    # Standard Bank Transactions and their provenance custom fields survive uninstall.
