"""Run on an isolated ERPNext test site; no Wise requests or real tokens are used."""

from decimal import Decimal
from uuid import uuid4

import frappe
from frappe.tests import IntegrationTestCase

from wise_bank_feed.core import key
from wise_bank_feed.importer import bank_entry, new

EXTRA_TEST_RECORD_DEPENDENCIES = ["Company"]


class TestWiseIntegration(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")
        suffix = uuid4().hex[:10]
        self.currency = frappe.get_value("Company", "_Test Company", "default_currency")
        parent = frappe.get_value(
            "Account", {"company": "_Test Company", "is_group": 1, "root_type": "Asset"}, "name"
        )
        account = frappe.get_doc(
            dict(
                doctype="Account",
                account_name="Wise " + suffix,
                company="_Test Company",
                parent_account=parent,
                is_group=0,
                account_type="Bank",
                account_currency=self.currency,
            )
        ).insert()
        bank = frappe.get_doc(dict(doctype="Bank", bank_name="Wise Test " + suffix)).insert()
        self.bank = frappe.get_doc(
            dict(
                doctype="Bank Account",
                account_name="Wise " + suffix,
                bank=bank.name,
                account=account.name,
                company="_Test Company",
                is_company_account=1,
            )
        ).insert()
        self.connection = frappe.get_doc(
            dict(
                doctype="Wise Connection",
                connection_name="Wise Test " + suffix,
                company="_Test Company",
                environment="Sandbox",
                api_token="synthetic-offline-token",
                profile_id=str(int(suffix, 16)),
                mode="Activity Review",
                start_date="2020-01-01",
                timezone="UTC",
                enabled=0,
            )
        ).insert()
        self.mapping = new(
            "Wise Account Map",
            connection=self.connection.name,
            balance_id="test-" + suffix,
            currency=self.currency,
            bank_account=self.bank.name,
            source_key=key(self.connection.name, suffix),
            available=1,
            enabled=1,
        )
        self.entry = {
            "reference": "WISE-" + suffix,
            "date": "2026-01-01",
            "deposit": Decimal("0"),
            "withdrawal": Decimal("12.34"),
        }
        self.payload = {"reference": self.entry["reference"], "amount": "-12.34"}
        self.source_key = key(self.connection.name, "booking", suffix)

    def import_booking(self, payload=None):
        return bank_entry(
            self.connection, self.mapping, self.source_key, self.entry,
            self.payload if payload is None else payload,
        )

    def test_submitted_bank_entry_is_idempotent_without_gl_postings(self):
        gl_count = frappe.db.count("GL Entry")
        booking = self.import_booking()
        self.assertEqual(self.import_booking().name, booking.name)
        rows = frappe.get_all("Bank Transaction", filters={"bank_account": self.bank.name}, fields=["*"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docstatus, 1)
        self.assertEqual(rows[0].status, "Unreconciled")
        self.assertAlmostEqual(float(rows[0].unallocated_amount), 12.34)
        self.assertEqual(rows[0].custom_wise_key, self.source_key)
        self.assertEqual(frappe.db.count("GL Entry"), gl_count)

    def test_changed_source_is_reviewed_without_rewriting_bank_amount(self):
        booking = self.import_booking()
        changed = self.import_booking({**self.payload, "amount": "-25.00"})
        self.assertEqual(changed.name, booking.name)
        self.assertEqual(changed.needs_review, 1)
        transaction = frappe.get_doc("Bank Transaction", booking.bank_transaction)
        self.assertEqual(transaction.custom_wise_review, 1)
        self.assertAlmostEqual(transaction.withdrawal, 12.34)
        self.assertEqual(transaction.docstatus, 1)
        self.assertTrue(frappe.db.exists("Wise Source Revision", {"source_name": booking.name}))

    def test_source_provenance_cannot_be_forged_or_cancelled(self):
        booking = self.import_booking()
        transaction = frappe.get_doc("Bank Transaction", booking.bank_transaction)
        transaction.custom_wise_key = "forged"
        with self.assertRaises(frappe.ValidationError):
            transaction.save()
        transaction.reload()
        with self.assertRaises(frappe.ValidationError):
            transaction.cancel()

    def test_skipping_booked_mapping_retains_bank_link_and_history(self):
        from wise_bank_feed.setup import save_mappings

        booking = self.import_booking()
        save_mappings(
            self.connection.name,
            [{"name": self.mapping.name, "bank_account": self.bank.name, "enabled": 0}],
        )
        self.mapping.reload()
        self.assertEqual(self.mapping.enabled, 0)
        self.assertEqual(self.mapping.bank_account, self.bank.name)
        self.assertEqual(frappe.get_value("Bank Transaction", booking.bank_transaction, "docstatus"), 1)

    def test_guest_cannot_read_setup_state(self):
        from wise_bank_feed.setup import state

        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                state(self.connection.name)
        finally:
            frappe.set_user("Administrator")
