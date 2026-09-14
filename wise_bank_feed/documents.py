import re
from zoneinfo import ZoneInfo

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today

from .core import key, validate_mapping


def lock_connection(name):
    frappe.db.sql("SELECT name FROM `tabWise Connection` WHERE name=%s FOR UPDATE", (name,))


class ManagedDocument(Document):
    def validate(self):
        if not self.flags.wise_internal:
            frappe.throw("This is a managed Wise record; use the Wise setup or review actions.")

    def on_trash(self):
        frappe.throw("Wise audit records cannot be deleted individually. Export them before uninstalling.")


class Connection(Document):
    def validate(self):
        frappe.only_for("System Manager")
        if not self.is_new():
            lock_connection(self.name)
        ZoneInfo(self.timezone)
        if getdate(self.start_date) > getdate(today()):
            frappe.throw("Historical start date cannot be in the future.")
        if self.profile_id and not re.fullmatch(r"\d+", self.profile_id):
            frappe.throw("Profile ID must be numeric.")
        self.profile_key = key(self.environment, self.profile_id) if self.profile_id else None
        if self.enabled and not self.profile_id:
            frappe.throw("Discover and select a Wise Business profile first.")
        old = self.get_doc_before_save()
        if old:
            source_exists = any(
                frappe.db.exists(t, {"connection": self.name})
                for t in ("Wise Activity", "Wise Booking", "Wise Account Map")
            )
            for field in ("profile_id", "company", "environment", "mode", "start_date", "timezone"):
                if source_exists and self.has_value_changed(field):
                    frappe.throw(f"{field} is immutable after discovery. Use a reviewed migration.")
            for field in ("cursor_at", "audit_at", "last_success", "status"):
                if not self.flags.wise_internal and self.has_value_changed(field):
                    frappe.throw("Sync status fields are managed by the connector.")

    def on_trash(self):
        lock_connection(self.name)
        if self.enabled or any(
            frappe.db.exists(t, {"connection": self.name})
            for t in ("Wise Activity", "Wise Booking", "Wise Account Map", "Wise Sync Log")
        ):
            frappe.throw(
                "Disable the feed and retain its audit records; only unused connections can be deleted."
            )


class AccountMap(Document):
    def validate(self):
        if not self.flags.wise_internal:
            frappe.only_for("System Manager")
        lock_connection(self.connection)
        c = frappe.get_doc("Wise Connection", self.connection)
        if not self.flags.wise_internal and c.enabled:
            frappe.throw("Pause the connection before changing account mappings.")
        if self.enabled and not self.bank_account:
            frappe.throw("Select a Bank Account or leave this mapping disabled.")
        if self.bank_account:
            bank = frappe.get_doc("Bank Account", self.bank_account)
            ledger = frappe.get_doc("Account", bank.account) if bank.account else {}
            validate_mapping(
                c.company,
                self.currency,
                bank.as_dict(),
                ledger.as_dict() if hasattr(ledger, "as_dict") else ledger,
            )
        old = self.get_doc_before_save()
        if old:
            for field in ("connection", "balance_id", "currency", "source_key"):
                if self.has_value_changed(field):
                    frappe.throw("Wise account identity is immutable.")
            if old.bank_account != self.bank_account and frappe.db.exists(
                "Wise Booking", {"account_map": self.name}
            ):
                frappe.throw("This account has bookings. Its ERPNext mapping cannot be changed.")
            for field in (
                "account_name",
                "balance_type",
                "investment_state",
                "reported_balance",
                "available",
                "cursor_at",
            ):
                if not self.flags.wise_internal and self.has_value_changed(field):
                    frappe.throw("Discovered account metadata is managed by the connector.")

    def on_trash(self):
        frappe.throw("Disable a mapping to skip it; retain its identity and audit history.")
