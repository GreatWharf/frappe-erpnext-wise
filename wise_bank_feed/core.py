"""Activity display strings are never parsed as ledger amounts."""

import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo


def key(*parts):
    return hashlib.sha256(json.dumps(parts, separators=(",", ":"), default=str).encode()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def amount(value):
    if value is None or isinstance(value, bool):
        raise ValueError("A finite decimal amount is required.")
    try:
        result = Decimal(str(value))
    except ValueError, InvalidOperation:
        raise ValueError("A finite decimal amount is required.") from None
    if not result.is_finite() or abs(result) > Decimal("9999999999999"):
        raise ValueError("Amount is outside supported limits.")
    return result


def validate_mapping(company, currency, bank, ledger):
    if (
        not bank.get("is_company_account")
        or bank.get("company") != company
        or not bank.get("account")
        or ledger.get("company") != company
        or ledger.get("account_currency") != currency
        or ledger.get("is_group")
        or ledger.get("disabled")
        or ledger.get("account_type") != "Bank"
    ):
        raise ValueError("Select a company Bank Account with a non-group Bank ledger in the same currency.")


def activity_identity(row):
    resource = row.get("resource") or {}
    if isinstance(resource, dict) and resource.get("id") is not None and resource.get("type"):
        return key("resource", resource["type"], str(resource["id"]))
    if not row.get("id"):
        raise ValueError("Activity has no stable identifier.")
    return key("activity", row["id"])


def statement_entry(row, currency, timezone):
    if not row.get("referenceNumber") or len(str(row["referenceNumber"])) > 140:
        raise ValueError("Statement line needs a stable reference number of at most 140 characters.")
    if row.get("type") not in ("CREDIT", "DEBIT"):
        raise ValueError("Unrecognized statement direction.")
    money = row.get("amount") or {}
    if money.get("currency") != currency:
        raise ValueError("Statement currency does not match mapping.")
    value = amount(money.get("value"))
    if value == 0 or (row["type"] == "CREDIT" and value < 0):
        raise ValueError("Amount is zero or contradicts credit direction.")
    booked = datetime.fromisoformat(str(row.get("date", "")).replace("Z", "+00:00"))
    if booked.tzinfo is None:
        raise ValueError("Booking timestamp needs a timezone.")
    return dict(
        reference=str(row["referenceNumber"]),
        date=booked.astimezone(ZoneInfo(timezone)).date().isoformat(),
        deposit=abs(value) if row["type"] == "CREDIT" else Decimal(0),
        withdrawal=abs(value) if row["type"] == "DEBIT" else Decimal(0),
    )
