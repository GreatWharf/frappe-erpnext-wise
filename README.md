# Wise Bank Feed for ERPNext v16

Independent, MIT-licensed Frappe app. Direct Wise personal-token access; no aggregator subscription, payment creation, bank writes, or direct GL posting. Initial release **0.1.0**. Requires Python 3.14, Frappe/ERPNext v16 and MariaDB, matching the existing Revolut app. The apps coexist and have separate DocTypes and provenance fields.

## What works in each mode

| Mode | Automatic work | Bank Transactions |
|---|---|---|
| Activity Review (default) | Discovers balances and refreshes activities every 15 minutes | Created only after an administrator confirms the exact booked account, amount, direction and date |
| Statements | Imports COMPACT JSON statement lines for enabled maps | Automatically creates and submits standard ERPNext Bank Transactions |

**This is not yet a complete automatic bank-reconciliation feed for UK personal tokens.** The user's live test returned HTTP 200 for profiles, activities and balances, but HTTP 403 with an SCA challenge for statements. Activity summaries contain formatted primary/secondary amounts which do not establish all booked account legs or fees. We intentionally do not guess. No claim is made that the Activities endpoint exposes every ledger event. Test a representative sample of card payments, refunds, transfers and FX against Wise before relying on coverage.

The module does not implement unsupported private website endpoints, legacy SCA signing, interactive SCA, OAuth partner onboarding or Wise webhook subscriptions. This version polls the public API. A free connector does not remove Wise's authentication restrictions. A personal API token does not refresh; replace it when revoked. Token retrieval is server-side via Frappe Password fields, never returned by setup endpoints.

## Browser setup

1. In Wise create a **read-only** personal API token for your business. Do not paste it into chat or commit it.
2. In ERPNext open **Wise Bank Feed** from the apps screen, or `/desk/wise-setup`.
3. Create a connection with your Company, token, timezone, start date and mode. Use Activity Review for the tested UK configuration. Save.
4. Click **Discover profiles**, choose the Business profile ID, then **Discover accounts**. The app shows balance ID, name, currency, balance type, investment state and reported available amount. Names do not imply account purpose; UUIDs/IDs are not guessed.
5. Open the accounts to map. Select an existing ERPNext company Bank Account linked to a Bank ledger of the same currency, then enable that mapping. The setup page also opens ERPNext's standard Bank Account creation form. **Leave any accounts unmapped/disabled.** Activity discovery works even with no mapped accounts.
6. Enable the connection, save, then **Sync Now**. Review **Sync logs** and the connection status. Pause the connection before editing mappings. Discovery refreshes names/balances without overwriting your maps. Unavailable accounts are retained but not imported.
7. In **Activity inbox**, inspect the source JSON (System Managers only). For a completed monetary activity, use **Create reviewed bank entry**, confirm the exact total posted amount including fees in the mapped account's currency, direction and booking date from Wise, and record evidence. For FX, create the appropriate entry for each affected mapped balance. One entry per activity/account/direction prevents repeat clicks; combine same-direction fees in the verified total rather than duplicate bookings.
8. **Finish review** only after checking all required legs, or document why an activity requires no booking. This does not declare the source a complete bank feed.

## Sync and history

Each run processes at most the next seven days of history, with a seven-day overlap for revisions. Pagination follows Wise's opaque cursor, capped at 100 pages per window; saturation or repeated cursors fail without advancing the checkpoint. Subsequent scheduled runs catch up automatically. Once current, only a recent window is fetched; this is not an all-history rescan. Activity mode also rechecks the latest 90 days weekly because Wise's `since` field is not documented as an update cursor. Changes older than that may remain undetected; periodic external reconciliation is required. Source disappearance is not interpreted as a reversal.

Statement checkpoints are per account: mapping a previously skipped balance imports it from the connection's start date. Activity history is profile-wide and remains available when you map an account later. Checkpoints and successful imports commit together. Errors roll back the job and retain a sanitized error log. Network/429/5xx errors have bounded retries. Authentication errors are not retried in a loop within a job. Fix credentials or SCA outside this app; then the next sync retries the unchanged window.

Original activity/statement IDs and full source JSON are retained. Source identity is scoped by environment/profile/balance, not the display name. Profile uniqueness prevents connecting the same Wise profile twice on one ERPNext site. Source revisions preserve evidence; changed imported records set **Wise Source Changed — Review Required**, block new reconciliation allocation changes and never silently rewrite existing booked amounts. Review source revisions, record necessary accounting adjustments through standard ERPNext workflows, then **Acknowledge source change** with an explanation. Original bank entries remain immutable and cannot be cancelled through this app. This release requires an administrator-led correction workflow rather than automated reversal accounting.

Statement mode uses one COMPACT line per transaction; reported fees and FX details are retained in the booking payload, not separately posted (which could double count). Unexpected currency/direction, zero values or duplicate references fail the whole window for review. The original statement schema and semantics should be validated on a live representative statement before production use. Switching modes/profile/company/timezone/start date after discovery is blocked to avoid cross-source duplication; mode migrations require a reviewed data migration.

## Permissions and data

Only System Managers configure connections, read Wise source records or perform reviewed bookings. Standard Bank Transactions retain ERPNext's normal accounting permissions. Multi-company mappings are validated against the connection company and ledger currency. API tokens are encrypted using the site's encryption key; back it up securely with the database. Activities, balances and source JSON are financial data stored in the site database, not secrets; access is restricted to System Managers. Logs exclude API tokens, challenge tokens, raw responses and traceback locals. Reverse proxies/APM tools must not log Authorization headers.

## Installation: normal Bench

Publish this source directory as a private or public Git repository, then use your actual repository URL:

```sh
bench get-app https://YOUR-GIT-HOST/YOUR-ORG/wise_bank_feed.git
bench --site YOUR_SITE install-app wise_bank_feed
bench --site YOUR_SITE migrate
bench build --app wise_bank_feed
```

These are server deployment operations. An arbitrary app cannot install its own Python code from an ERPNext browser screen; all configuration after installation is in Desk.

## Docker / Dokploy with your existing image

Use the same pinned ERPNext v16 image you currently deploy as `BASE_IMAGE`, including your Revolut app if present. The example extends it; it does not replace your database, Redis, sites volume or networking. Build from this repository root:

```sh
docker build -f docker/Dockerfile --build-arg BASE_IMAGE=YOUR_CURRENT_PINNED_IMAGE -t YOUR_REGISTRY/erpnext-with-wise:0.1.0 .
docker push YOUR_REGISTRY/erpnext-with-wise:0.1.0
```

The sample assumes your base image includes Node and build tools. If it is runtime-only, add this repository to the `apps.json` used by your existing frappe_docker custom-image build instead. Preserve existing apps, including Revolut. No GitHub Actions are required. Do not use a made-up release tag or switch your existing ERPNext major version.

Point **all Frappe services** at the new identical image: backend, frontend, websocket, scheduler, short worker and long worker. A live `sites` volume can hide the image's `sites/apps.txt`; merge `wise_bank_feed` into that volume's existing apps list through your existing configurator. Preserve all prior entries. Ensure `sites/assets` serves the new app assets using your existing deployment's asset-refresh procedure; building assets into an image alone does not refresh a volume masking that directory.

Use one serialized Dokploy deployment initializer, after backups and while traffic/workers are paused, with the same sites volume and network as backend:

```sh
WISE_SITE=YOUR_EXISTING_SITE sh apps/wise_bank_feed/docker/deploy-site.sh
```

This script idempotently installs the app if absent and runs migrate. Put it into your existing deployment lifecycle; do not run it in every worker startup or multiple Swarm replicas. Site registration is a database operation and still has to happen once per site, even when app code is baked into the image. It need not be a manually repeated Bench command. Resume normal services after successful initialization. Use Dokploy's supported task ordering rather than relying on Compose `depends_on` in Swarm.

## Scheduler and workers

Enable the site's scheduler, run scheduler service plus Redis queue and a worker consuming `long`; jobs have a 900-second timeout and Redis deduplication/lock. Sync Now queues work; it does not execute the full sync inside an HTTP request. A disabled scheduler still permits manual queued sync if workers run. Jobs refresh balances and source data while serialized against connection/mapping changes.

## Upgrades, troubleshooting and uninstall

Back up database, private files and site configuration/encryption key. Rebuild the shared image from the new source, refresh shared assets/apps list, run the serialized migration initializer, then restart services. Never upgrade only backend while workers use old code.

- **403 with SCA:** statement access requires additional authentication. Activity Review remains a separate mode; this app cannot authorize SCA automatically. Pause a Statements connection until resolved.
- **401:** replace the revoked/incorrect token. Check Production vs Sandbox.
- **No new records:** check date range, profile, enabled state, scheduler/long worker and Sync Log. A successful empty activity page is not proof no money moved.
- **Schema/validation error:** checkpoint remains unchanged. Compare source schema and account currency; use the local access test for diagnosis without sharing tokens. Logs intentionally omit raw response/error text.
- **Mapped account disabled:** pause, edit, save and resume. Previously imported entries remain.
- **Missing menu/assets:** run migrate and build/refresh assets on the shared sites volume, then reload Desk.

For uninstall, disable connections, drain jobs, resolve changed-booking reviews and export all Wise source/revision records. Run `bench --site YOUR_SITE uninstall-app wise_bank_feed` in your normal maintenance process. Source DocTypes are removed; standard Bank Transactions and Wise provenance custom fields deliberately remain. Archive those fields before any manual removal. Reinstalling without restoring source history is not a supported way to reset sync; it can lose duplicate-prevention context.

## Validation and current limitations

Run `python -m pytest` from this directory for mocked API and pure import validation. This repository is a first release, not a claim of production certification: no live Frappe/ERPNext bench or Docker engine was available for end-to-end verification. Validate installation, permissions, repeated imports, rollback and reconciliation on a staging site before production. No live token was stored or reused from the earlier access test.

Official references checked during implementation:
- https://docs.wise.com/api-reference/activity
- https://docs.wise.com/api-reference/balance
- https://docs.wise.com/api-reference/balance-statement/balancestatementget
- https://docs.wise.com/guides/developer/auth-and-security/personal-api-token
