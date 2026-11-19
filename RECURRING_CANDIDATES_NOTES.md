# Recurring-charge candidates, supplied rows only

This pure module does not read a provider, expose an MCP tool, write a file or predict a future debit. It is disconnected from the fixture server and all admin flows.

`recurring_charge_candidates(records)` accepts the same closed normalized row contract as transaction analytics, at most 1000 rows. A candidate requires:

- A booked negative amount in a known currency.
- An original transaction date, not a booking/value-date fallback.
- The same exact, nonblank description, currency and Decimal amount.
- At least three distinct dates. Every consecutive interval must be between25and35days inclusive.

The description is an untrusted label, not verified merchant identity. There is no approximate merchant matching, model classification, amount tolerance, exchange conversion, database or clock lookup. Harmless numeric scale differences such as9.99and9.9900 group using exact Decimal equality within a private64digit context.

Output provides the supporting dates, interval lengths, distinct-date count and input-row count. Multiple rows on one date cannot manufacture recurrence evidence. This is NOT transaction deduplication and does not correct or aggregate totals. Exact repeated descriptions and amounts can still represent unrelated purchases, so every candidate is `unverified_pattern`, never a confirmed subscription or obligation.

The approach intentionally misses variable prices, weekly/annual cycles, description changes, missing months, date fallbacks and irregular billing. No next-charge date is calculated. A monthly25..35day pattern is not proof of a contract or a forecast. Empty output means no matching pattern in the supplied rows, not no subscriptions.

Exclusion counts use the first matching reason only, in this order: pending, nondebit, unknown currency, unreliable date, blank description. Invalid normalized input stops the entire analysis with its existing generic error.

## Reuse

Grouping/cadence pattern adapted from guille-near/openbanking-mcp at d61e3ad67b60aa848d96887fd4d06dc3fefbd749, source `src/finmcp/analytics/subscriptions.py`. MIT copyright2026GuillePérez and full license retained in LICENSES/guille-near-openbanking-MIT.txt. The original uses database queries, mean/relative tolerance and median cadence. This adaptation removes those paths, requires three dates and every gap within the bound, and uses no float money.

Pinned source inspected: https://raw.githubusercontent.com/guille-near/openbanking-mcp/d61e3ad67b60aa848d96887fd4d06dc3fefbd749/src/finmcp/analytics/subscriptions.py . This documents a pinned extraction, not live bank compatibility.
