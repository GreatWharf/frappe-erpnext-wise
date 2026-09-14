# Wise Bank Feed v0.1 implementation plan

Goal: independent installable ERPNext/Frappe v16 app with direct personal-token GET access.
Architecture: encrypted connection -> discovered balances -> optional immutable maps -> scheduled activity inbox. Statement mode is a separate, immutable choice with authoritative statement imports. Activity mode requires explicit reviewed booking legs because activity amounts are formatted summaries, not a complete ledger schema.

1. Pure core and mocked client tests: deterministic source identity, Decimal amounts, currency/company mapping, statement normalization, pagination exhaustion, 403 SCA redaction, GET-only paths.
2. Frappe DocTypes: connection, account map, activity, booking leg, source revision and sync log. Unique keys enforce idempotency across connections. Internal records read-only via API except explicit review operations.
3. Sync: serialized per connection, finite 7-day historical windows, 7-day incremental overlap, weekly 90-day activity audit. Per-map statement checkpoints support mappings added later. Successful window only advances; rollback failed jobs. Never overwrite submitted/reconciled bank entries on source revisions.
4. Desk setup + forms: token/profiles, refresh accounts, optional mapping, activate/pause, sync now, review booking legs with human-confirmed amount/direction/date. Show limited activity-mode coverage prominently.
5. Docker custom-image example and serialized site installer, docs and archive. Run pure/mock tests, JavaScript syntax, package validation. Live Frappe/Docker testing unavailable in this workspace; document explicitly.
