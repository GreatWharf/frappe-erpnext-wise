# Changelog

## 0.3.2 — Marketplace static-scan remediation

- Build navigation documents (Workspace sidebar, Desktop Icon) from static Python data instead of reading bundled JSON at runtime. No `open()` calls remain in production code paths; fixtures stay on disk and new tests assert the builders match them exactly.
- Inline the CI failure-tail annotation into the workflow shell step and remove the `scripts/run_ci.py` subprocess wrapper. No dynamic process execution remains.
- Add navigation test coverage (`tests/test_navigation_data.py`). No banking logic or schema changes.

## 0.3.1 — Marketplace version-range correction

- Change the Frappe compatibility ceiling from `<17.0.0-dev` to the stable `<17.0.0` required by Frappe Cloud's range validator. v16 support is unchanged.
- Add regression checks for the compatibility range and matching package/app versions. No banking logic or schema changes.
- Use tag `v0.3.1`, or refresh the existing `release/0.3.0` branch in Frappe Cloud. The older `v0.3.0` tag remains unchanged and contains the rejected metadata.

## 0.3.0 — 2026-09-16

Release candidate for Frappe/ERPNext v16, Python 3.14 and MariaDB. Existing version tags are retained.

- Fix first-time setup: the API client now closes its HTTP session correctly when used by the connection wizard.
- Separate account inclusion from its ERPNext mapping. Skip or disable a previously booked/unavailable account without erasing its historical Bank Account link.
- Replace the connection-form button cluster with Setup and View menus and one prominent next action: Continue setup or Sync Now.
- Preserve the selected connection when reopening setup; make Statements-mode labels and navigation accurate.
- Prevent duplicate manual sync requests while a request is running and guard actions against unsaved changes.
- Add offline client/mapping regressions, JavaScript behavior tests, and real-site installation/migration/Bank Transaction integration CI.
- Validate runtime files in both wheel and source distributions; run release checks on branches and tags.

### Upgrade

Back up your database, private files, and site encryption key. Update to this release and run `bench --site <site> migrate`, then rebuild/restart using your deployment's normal procedure. Existing account links and audit records are preserved. Review the first sync on a staging site before enabling it in production.

### Validation boundaries

Offline tests do not prove Wise token/region access or live-account completeness. The real-site workflow uses synthetic data and no bank credentials. Check the exact release commit's GitHub Actions results and complete the [staging checklist](docs/verification.md) before production use. A Git tag does not mean the app has received Frappe Marketplace approval.

## 0.2.2

- Declare Frappe v16 compatibility for Frappe Cloud.

## 0.2.1

- Preserve the Wise app icon in existing desktop layouts.

## 0.2.0

- Add guided connection setup and home-screen navigation.

## 0.1.1

- Harden synchronization and import validation.
