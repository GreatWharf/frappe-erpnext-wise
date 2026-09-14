# Verification — v0.1.1

## Automated checks

**79 tests pass under Python 3.14.** GitHub Actions runs them on pushes and pull requests.

| Area | Covered |
| --- | --- |
| Wise HTTP contract | Versioned endpoints, Bearer token, GET-only allowlist, redirects blocked, COMPACT statements, decimal precision |
| Pagination and retries | Opaque cursors, invalid/missing/repeated cursors, page cap, HTTP/network retries, long rate limits, job deadline |
| Token-to-sync flow | Business-profile selection, account discovery, activity import without mappings, repeated sync, weekly history audit |
| Bookings | Duplicate prevention, COMPACT fees counted once, explicit reviewed entries, missing dates, source revisions and acknowledgement |
| Failures | Partial-page and second-account errors roll back imported records and checkpoints; sanitized error logs remain |
| Permissions and mapping | System Manager access, company/currency checks, optional mappings, pause-before-edit, immutable source identity |

The flow tests run the real client, discovery, importer, review and sync functions. Only HTTP, the clock and Frappe storage/runtime boundaries are simulated. They do **not** prove MariaDB transaction isolation, live permissions or ERPNext reconciliation behavior.

Also checked locally: Ruff, Desk JavaScript syntax, DocType JSON and Python wheel/source builds.

## Wise contract checked

Checked against Wise’s 2026Q3 documentation on 14 September 2026:

- [Activity](https://docs.wise.com/api-reference/activity): personal-token access, `since`/`until`, `cursor` → `nextCursor`, up to 100 results per page.
- [Balances](https://docs.wise.com/api-reference/balance): standard balances and savings jars, names, currencies and investment metadata.
- [Statements](https://docs.wise.com/api-reference/balance-statement): COMPACT lines include fees; statement access is SCA-protected in affected regions.
- [Personal tokens](https://docs.wise.com/guides/developer/auth-and-security/personal-api-token): statement retrieval is supported only for accounts based in US, CA, AU, NZ, SG and MY.

Activity summaries do not establish every booked account leg or fee. They are never parsed into automatic bank entries.

## Still needs a staging site

No live Wise token, Frappe Bench, MariaDB, Redis or Docker runtime was available for this review. No production sync was run.

Before relying on the feed:

1. Install alongside existing apps on ERPNext v16 staging.
2. Save a read-only token; discover the correct business profile and balances.
3. Leave one account unmapped. Sync twice and confirm no duplicate records.
4. Confirm scheduler/long-worker sync continues after closing the browser.
5. Review a card payment, refund, transfer and FX transaction against Wise; check each affected account and fees.
6. Create a reviewed bank entry and reconcile through ERPNext’s normal workflow.
7. For Statements mode, confirm regional/token access and compare imported totals with a downloaded Wise statement.
8. Check permissions, a rejected token and overlapping jobs on the real database.
