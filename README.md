<p align="center">
  <img src="docs/images/integration.svg" alt="ERPNext ↔ Wise" width="480" />
</p>

<h1 align="center">Wise Bank Feed</h1>
<p align="center">Your Wise Business activity, inside ERPNext.</p>
<p align="center"><strong>Unofficial · ERPNext v16 · MIT licensed</strong></p>

Built for our internal use at Great Wharf and shared for others to use and improve. This project is not affiliated with or endorsed by Wise or Frappe.

## What it does

- Connects directly to Wise with a **read-only API token**.
- Discovers your business profiles and balances.
- Lets you choose which accounts to map. Leave the rest unmapped.
- Refreshes activity every **15 minutes**.
- Creates standard ERPNext Bank Transactions for reconciliation.
- Keeps API tokens encrypted on your ERPNext server.
- Coexists with our [Revolut Bank Feed](https://github.com/GreatWharf/erpnext_revolut).

## Choose your mode

| Mode | How entries reach ERPNext |
| --- | --- |
| **Activity Review** — default | Review collected activity, confirm the booked amount, fees, account and date, then create a bank entry. |
| **Statements** | Automatically imports statement lines when your Wise token has statement API access. |

**UK or European Wise account? Use Activity Review.** Wise’s [personal-token guide](https://docs.wise.com/guides/developer/auth-and-security/personal-api-token) limits statement retrieval to accounts based in the **US, Canada, Australia, New Zealand, Singapore and Malaysia**. This app does not implement additional authentication (SCA) or partner access.

Activity summaries are not a complete bank statement; verify them against Wise before booking.

- No payments, Wise account changes or direct general-ledger posting.
- Initial release: validate your account’s coverage on a staging site.

## Install

Requires **Frappe + ERPNext v16**, **Python 3.14** and **MariaDB**.

```sh
bench get-app https://github.com/GreatWharf/erpnext_wise.git
bench --site YOUR_SITE install-app wise_bank_feed
bench --site YOUR_SITE migrate
bench build --app wise_bank_feed
```

Using Docker or Dokploy? Follow the [deployment instructions](docs/operations.md#docker--dokploy-with-your-existing-image).

## Connect

1. In Wise Business, open **Your Account → Connect and manage apps → API tokens**. Create a **read-only token**.
2. Open **Wise Bank Feed** in ERPNext’s apps screen, or go to `/desk/wise-setup`.
3. Create a connection. Choose your company, token, start date and **Activity Review** mode.
4. Save → **Discover profiles** → select your business → **Discover accounts**.
5. Map only the accounts you want to an ERPNext Bank Account of the same currency.
6. Enable the connection → **Sync Now** → open **Activity inbox** to review.

Configuration and activity review require the **System Manager** role. Pause a connection before changing its mappings.

## Help & development

- [Setup, data coverage and operations](docs/operations.md)
- [Troubleshooting](docs/operations.md#upgrades-troubleshooting-and-uninstall)
- [Report an issue](https://github.com/GreatWharf/erpnext_wise/issues) — leave out tokens and financial data.
- Run tests: `python -m pytest` — [test coverage and live-testing limits](docs/verification.md).
- GitHub Actions runs tests, lint, JavaScript syntax checks and packaging on each push and pull request.

[MIT license](LICENSE). Wise and ERPNext logos belong to their respective owners; see [logo sources](docs/images/README.md).
