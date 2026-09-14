"""CLI only. Called by a serialized site initializer after code is built into the image."""

import frappe
from frappe.installer import install_app

from .install import check_versions


def ensure_installed():
    if not frappe.local.site or frappe.session.user != "Administrator":
        frappe.throw("Run from the deployment initializer as Administrator with a selected site.")
    check_versions()
    if "erpnext" not in frappe.get_installed_apps():
        frappe.throw("Install ERPNext v16 first.")
    if "wise_bank_feed" not in frappe.get_all_apps():
        frappe.throw("Image apps.txt must include wise_bank_feed.")
    if "wise_bank_feed" in frappe.get_installed_apps():
        return {"status": "already_installed"}
    install_app("wise_bank_feed", verbose=True)
    return {"status": "installed"}
