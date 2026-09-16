# Wise Bank Feed validation notes

This page records what has been checked and what still needs to be confirmed on a real ERPNext site.

## Automated checks

The local test suite covers the Wise API client, profile and balance discovery, activity pagination, reviewed bank entries, duplicate prevention, fees, FX records, changed source records, permissions, and safe error handling. It also checks that tokens and private response data do not appear in logs.

The tests use mocked API responses and a lightweight Frappe boundary. They do not replace a staging run against your own ERPNext site, database, scheduler, workers, or Wise account.

## Release 0.3.0 checks

On 16 September 2026, the local Python 3.14 run passed **100 offline tests** and **11 Node UI behavior tests**. These exercise context-manager cleanup, inclusion without unlinking booked accounts, selected-connection routing, grouped actions, and dirty/in-flight guards. They are not a live-browser screenshot review.

Reproduce from the repository root:

```sh
python -m pip install -e '.[test]'
python -m pytest -q
node --test tests/test_ui.js
ruff check wise_bank_feed tests scripts
find wise_bank_feed -name '*.js' -print0 | xargs -0 -n1 node --check
python -m build
python scripts/check_dist.py
```

The **Frappe v16 integration** workflow installs this app on an isolated MariaDB-backed Frappe/ERPNext site, runs migration, and checks actual submitted Bank Transactions, duplicate prevention, source-change review, provenance protection, and mapping history. It uses synthetic data, not a Wise account. A workflow being configured is not evidence of a successful run: inspect the [Actions results](https://github.com/GreatWharf/frappe-erpnext-wise/actions) for the exact tag/commit.

## Wise access limits

- Activity access can return profiles, balances, and recent activity while still leaving older history incomplete.
- Activity summaries do not always describe every booked account leg or fee, so Activity Review requires a human check before creating a Bank Transaction.
- Statement access is protected by Wise's regional rules and may require additional authentication.
- Personal-token statement access is currently limited to accounts based in the United States, Canada, Australia, New Zealand, Singapore, and Malaysia.

See Wise's [Activity API](https://docs.wise.com/api-reference/activity), [Balances API](https://docs.wise.com/api-reference/balance), [Balance Statement API](https://docs.wise.com/api-reference/balance-statement/balancestatementget), and [personal-token guide](https://docs.wise.com/guides/developer/auth-and-security/personal-api-token).

## Before relying on the feed

1. Connect a read-only token on a staging site.
2. Choose the correct business profile and leave one unfamiliar account unmapped.
3. Sync twice and confirm that the same activity does not create duplicates.
4. Compare a card payment, refund, transfer, and FX item with Wise.
5. Create one reviewed Bank Transaction and reconcile it through ERPNext.
6. If you use Statements mode, confirm that Wise permits it for your region and token.
