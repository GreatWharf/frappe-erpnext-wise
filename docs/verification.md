# Wise Bank Feed validation notes

This page records what has been checked and what still needs to be confirmed on a real ERPNext site.

## Automated checks

The local test suite covers the Wise API client, profile and balance discovery, activity pagination, reviewed bank entries, duplicate prevention, fees, FX records, changed source records, permissions, and safe error handling. It also checks that tokens and private response data do not appear in logs.

The tests use mocked API responses and a lightweight Frappe boundary. They do not replace a staging run against your own ERPNext site, database, scheduler, workers, or Wise account.

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
