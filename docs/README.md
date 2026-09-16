# Wise Bank Feed help

This guide explains how to connect Wise to ERPNext, review activity, and create bank entries safely.

## Before you start

- You need a Wise Business account and a **read-only personal API token**.
- You need ERPNext v16 with the app installed.
- You need an ERPNext **System Manager** account for the first connection.

Wise decides which data is available for each account and region. Read [Wise's personal-token limits](https://docs.wise.com/guides/developer/auth-and-security/personal-api-token) before subscribing.

## Choose a guide

| You want to… | Read this |
| --- | --- |
| Connect Wise and review activity | [Setup and everyday use](operations.md) |
| Understand statement restrictions | [Setup and everyday use](operations.md#activity-review-and-statements) |
| Check what has been tested | [Verification notes](verification.md) |

## The recommended flow

1. Add your read-only token in **Wise Bank Feed**.
2. Choose the Wise business profile shown by the setup guide.
3. Review the balances and match only the ERPNext Bank Accounts you recognise.
4. Let new activity arrive, then review it before creating Bank Transactions.
5. Reconcile approved entries using ERPNext's normal banking tools.

You can leave unfamiliar Wise accounts unmapped. Discovering an account does not import it.

## Important limits

Activity Review is the default and most broadly available option. Automatic Statements depend on Wise's regional rules and may require extra authentication. UK and European accounts should use Activity Review.

The app is read-only. It does not send payments, change Wise settings, or post directly to the general ledger.
