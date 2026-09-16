# Wise Bank Feed: setup and everyday use

[Back to Wise Bank Feed help](README.md)

## Activity Review and Statements

| Mode | What it does | Best for |
| --- | --- | --- |
| **Activity Review** | Brings recent Wise activity into ERPNext for you to check before creating a Bank Transaction. | Most users, including UK and European accounts |
| **Automatic Statements** | Imports statement lines and can create standard Bank Transactions automatically for enabled accounts. | Accounts and regions where Wise allows statement access |

Activity Review is the recommended starting point. Activity data can be a summary rather than a complete ledger, so confirm the amount, date, fees, and every affected account before creating an entry.

## Before you start

- A Wise Business account.
- A **read-only personal API token** from **Your Account → Connect and manage apps → API tokens** in Wise.
- An ERPNext Company and Bank Accounts for the currencies you want to use.
- An ERPNext **System Manager** login.

Never paste the token into chat, screenshots, or source code.

## Connect Wise

1. Open **Wise Bank Feed** from the ERPNext home screen, or open `/desk/wise-setup`.
2. Enter your Company, token, timezone, start date, and preferred mode.
3. Choose **Discover profiles**, then select the Wise business profile you want to use.
4. Choose **Discover accounts** and review the profile ID, balance ID, name, currency, and balance.
5. Match only the accounts you recognise to ERPNext Bank Accounts with the same currency. Leave the rest blank.
6. Save and enable the connection, then choose **Sync now**.

The setup page saves your progress. You can return later, refresh account names and balances, or add another account match without remapping everything.

## Review activity and create a bank entry

1. Open **Activity inbox**.
2. Open a completed activity and compare it with Wise.
3. Confirm the exact amount, currency, date, direction, fees, and every affected account.
4. Choose **Create reviewed bank entry** when the details are correct.
5. Reconcile the resulting Bank Transaction through ERPNext.

For FX activity, review each affected currency account separately. Do not create two entries for the same fee.

## Automatic Statements

Personal-token statement access is currently supported only for Wise accounts based in the **United States, Canada, Australia, New Zealand, Singapore, and Malaysia**. Wise may require extra authentication for statements. UK and European accounts should use Activity Review. [Wise personal-token limits](https://docs.wise.com/guides/developer/auth-and-security/personal-api-token) · [Wise statement requirements](https://docs.wise.com/api-reference/balance-statement/balancestatementget)

This app cannot complete Wise's additional authentication inside ERPNext. If Wise returns an authentication challenge, pause Statements mode and use Activity Review unless you have separately confirmed access.

## Sync and history

- New activity is checked automatically about every **15 minutes** while the connection is enabled.
- The app keeps a small overlap between syncs so late updates can be noticed.
- Activity history is not an unlimited historical export. An empty result does not prove that no older money moved.
- Adding a mapping later makes the account available for future reviewed entries; it does not guess or rewrite past accounting.
- If Wise changes a source record after you reviewed it, ERPNext keeps the original evidence and asks for a fresh review.

## Common problems

| What you see | What to try |
| --- | --- |
| I cannot find Wise Bank Feed | Sign in as a **System Manager**, search for **Wise Bank Feed**, and reload ERPNext after an app update. |
| Profiles or balances are empty | Check the token, Production/Sandbox choice, profile selection, and date range. A successful empty response does not prove there is no history. |
| Accounts are listed but nothing imports | Enable the connection, match at least one account for reviewed entries, and choose **Sync now**. |
| Wise returns 403 or asks for extra authentication | This is usually a Statements restriction. Use Activity Review or complete the Wise authentication outside this app. |
| A token returns 401 | Replace the revoked or incorrect token with a new read-only token. |
| An account is unfamiliar | Leave it unmapped. Account discovery does not require importing it. |
| No new activity appears | Check the date range, profile, connection status, scheduler, and **Sync logs**. |

## Permissions and data

System Managers configure connections, view Wise source records, and create reviewed entries. Standard ERPNext Bank Transactions keep ERPNext's normal permissions.

Tokens are encrypted by ERPNext. Wise activities, balances, and review evidence are financial data stored in your site database. Keep your normal ERPNext backups and site encryption key safe.

## Reporting a problem

Include the app version, ERPNext version, visible error message, profile or balance ID, and what you were doing. Remove names, amounts, tokens, and other private financial details from screenshots.
