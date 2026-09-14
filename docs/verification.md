# Verification — v0.1.0

22 pure/mocked tests passed under Python 3.14.7. Coverage: money validation, company/currency mapping, scoped IDs, API pagination and SCA redaction, duplicate imports, orphan provenance, unchanged/changed source handling, date/Decimal/allocation guards, successful checkpoints and failure rollback orchestration.

Ruff lint and formatting passed. All four Desk JavaScript files passed Node syntax checks. Six DocType JSON schemas parsed with consistent field_order. Deployment shell syntax passed. Python wheel and source distribution built successfully.

No live ERPNext, MariaDB, Redis, browser interaction or Docker image build was run. Mock tests do not prove transaction isolation or Frappe deployment compatibility. Staging acceptance: install alongside Revolut, connect a read-only token, discover balances, save an optional mapping, enable and sync twice, verify no duplicate source records, create/retry a reviewed entry, and verify normal reconciliation. Test SCA failure leaves statement checkpoints unchanged and test source-change review with a controlled fixture before enabling Statement mode. Compare totals against Wise for each currency.
