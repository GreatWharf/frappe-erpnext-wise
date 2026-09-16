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

## Wise access and limitations

You need a Wise Business account and a **read-only personal API token**. Wise controls which data each account and region can provide, so the available history and features can vary. See [Wise's personal-token limits](https://docs.wise.com/guides/developer/auth-and-security/personal-api-token) before subscribing.

**Activity Review** is the default and most broadly available option. It brings recent Wise activity into ERPNext for you to check before creating a Bank Transaction. A successful activity response does not guarantee that every historical ledger entry is available.

**Automatic Statements** are more limited. With personal tokens, Wise currently supports statement access only for accounts based in the **United States, Canada, Australia, New Zealand, Singapore, and Malaysia**. Wise may also require extra authentication for statement access. UK and European accounts should use Activity Review.

You also need ERPNext v16 and an ERPNext System Manager account for the first connection.

## Getting started

1. Install the app from the Frappe Marketplace.
2. Open **Wise Bank Feed** from the ERPNext home screen, or open `/desk/wise-setup`.
3. Enter your company, read-only token, and the date from which you want to review activity.
4. Choose the Wise business profile shown by the setup guide.
5. Select the Wise accounts you want and match them to ERPNext Bank Accounts. Skip the rest without removing any existing account links.
6. Start the feed, then open the activity inbox to review the first results.

The setup guide saves your progress, so you can return to it later. API tokens are stored encrypted on your ERPNext site. Keep your normal ERPNext backups and site encryption key safe.

## How syncing works

The app reads Wise activity and creates standard ERPNext Bank Transactions after review. It does not send payments, change Wise account settings, or post directly to the general ledger. Check the first import against Wise before reconciling it.

## Help

- [Setup and operations](docs/operations.md)
- [Troubleshooting](docs/operations.md#upgrades-troubleshooting-and-uninstall)
- [Release notes and upgrade](CHANGELOG.md)
- [Verification notes](docs/verification.md)
- [Report an issue](https://github.com/GreatWharf/frappe-erpnext-wise/issues) — never include credentials or financial data.

## License

This project is MIT licensed.
