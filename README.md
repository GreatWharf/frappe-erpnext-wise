<p align="center">
  <img src="docs/images/integration.svg" alt="ERPNext and Wise" width="480" />
</p>

# Wise Bank Feed for ERPNext

**Unofficial · Read-only · ERPNext v16 · MIT licensed**

Wise Bank Feed brings your Wise Business activity into ERPNext so you can review transactions and reconcile your accounts in one place. It was built for internal use at Great Wharf and is shared as an independent community app. It is not affiliated with Wise or Frappe.

## What you can do

- Connect a Wise Business account with a read-only API token.
- Choose the Wise business profile you want to use.
- See the balances available to that profile.
- Match only the accounts you want to ERPNext Bank Accounts.
- Leave unfamiliar accounts unmapped until you know what they are.
- Sync new activity automatically every 15 minutes.
- Review the amount, date, account, and supporting details before creating a Bank Transaction.
- Reconcile approved entries using ERPNext’s normal banking tools.
- Keep the connection read-only: ERPNext cannot send payments through this app.

## Activity review, explained simply

Wise activity sync is the default and recommended option. It brings in recent activity for you to review before it becomes an ERPNext Bank Transaction. This gives you a chance to confirm the amount, date, fees, and account first.

Some Wise accounts also support automatic statements. Availability depends on Wise and the account connected to your token. UK and European accounts should use Activity Review.

## What you need

- Frappe and ERPNext v16.
- A Wise Business read-only API token.
- An ERPNext System Manager account for the initial setup.

## Getting started

1. Install the app on your ERPNext site.
2. Open **Wise Bank Feed** from the ERPNext home screen, or open `/desk/wise-setup`.
3. Enter your company, read-only token, and the date from which you want to review activity.
4. Choose the Wise business profile shown by the setup guide.
5. Match the Wise accounts you want to ERPNext Bank Accounts. Leave the rest blank.
6. Start the feed, then open the activity inbox to review the first results.

The setup guide saves your progress, so you can return to it later. API tokens are stored encrypted on your ERPNext site. Keep your normal database backups and site encryption key safe.

## Installing on a self-hosted bench

```sh
bench get-app https://github.com/GreatWharf/frappe-erpnext-wise.git
bench --site YOUR_SITE install-app wise_bank_feed
bench --site YOUR_SITE migrate
bench build --app wise_bank_feed
```

Frappe Cloud users can install the app from the Marketplace once it is approved.

## How syncing works

The app reads Wise activity and creates standard ERPNext Bank Transactions after review. It does not send payments, change Wise account settings, or post directly to the general ledger. Check the first import against Wise before reconciling it.

## Help

- [Setup and operations](docs/operations.md)
- [Troubleshooting](docs/operations.md#upgrades-troubleshooting-and-uninstall)
- [Verification notes](docs/verification.md)
- [Report an issue](https://github.com/GreatWharf/frappe-erpnext-wise/issues) — never include credentials or financial data.

## License

This project is MIT licensed. Wise and ERPNext names and logos belong to their respective owners. See [logo sources](docs/images/README.md).
