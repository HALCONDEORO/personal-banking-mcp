# Pure transaction search and summaries prototype

No network, provider, credentials, storage, background work, MCP registration or automatic classification. Two pure functions accept a caller-supplied bounded list of normalized transaction records. This is an isolated experiment, not a live bank analytics product or a complete financial report.

`search_transactions` matches a bounded casefolded literal substring against description only. No regex, fuzzy/AI match or arbitrary query language. Optional ISO date bounds are inclusive and apply to the normalized date, including explicitly labeled booking/value fallbacks. Undated rows are excluded when dates are filtered. Results preserve input order, copy the shallow scalar-only rows and report matched input count/truncation. Empty query matches supplied rows. No pagination or provider read happens implicitly.

`summarize_transactions` separates every currency and pending/booked status. Amounts are validated bounded decimal strings, never floats. Uses its own64digit Decimal context; at most1000rows,15integer+8fractional digits each. Output amounts are fixed-point strings, not rounded to assumed two-decimal currency precision. Inflow, positive outflow and signed net are separate. Positive refunds are inflow, not silently removed from category outflow. Unknown currency XXX stays in its own labeled bucket, without conversion or aggregation with known currency.

Category precedence adapts upstream: explicit user label, then provider label, then Uncategorized. This does not infer that any label is correct. Only negative rows contribute to category outflow; grouping is still separate by currency/status. Date fallback/unknown counts are visible. No budget advice, recurring-charge prediction or anomaly claim.

## Caller obligations and limits

- Supply one known selection of normalized rows with no accidental overlap. This module does not fetch additional pages and does not guess duplicate identities. Duplicate input rows count twice and output says deduplication not performed.
- Output scope is always supplied_rows_only, history_completeness not_verified. Even an empty input is not evidence of no real transactions. Never replace this with a complete-history claim because a page happened to have no cursor.
- Inputs accept only amount/currency/currency_known/status/date/date_source/date_inferred/description plus optional user_category/provider_category. No account, IBAN, merchant or arbitrary provider fields. Descriptions and category labels may still be private/untrusted content; no logging and no automatic disclosure.
- Provider category or supplied user-category text is data, never an instruction or evidence of the owner's choice. A future authorized UI must ground the real user action separately. No category editing/persistence is performed here.
- Generic validation errors do not include record values. This does not erase private Python memory or prevent a caller from printing locals.

## Adaptation provenance and full license texts

Category precedence and per-category aggregation structure adapted from guille-near/openbanking-mcp pin d61e3ad67b60aa848d96887fd4d06dc3fefbd749, MIT, Copyright(c)2026 Guille Pérez. Sources:
https://raw.githubusercontent.com/guille-near/openbanking-mcp/d61e3ad67b60aa848d96887fd4d06dc3fefbd749/src/finmcp/analytics/categories.py
https://raw.githubusercontent.com/guille-near/openbanking-mcp/d61e3ad67b60aa848d96887fd4d06dc3fefbd749/src/finmcp/analytics/summaries.py
Full license: LICENSES/guille-near-openbanking-MIT.txt.

Literal text-search pattern adapted from elcukro/bank-mcp pin c6abad503b1ecec47e80108ef8d0c614da0f4de5, MIT, Copyright(c)2026 bank-mcp contributors:
https://raw.githubusercontent.com/elcukro/bank-mcp/c6abad503b1ecec47e80108ef8d0c614da0f4de5/src/tools/search-transactions.ts
Full license: LICENSES/elcukro-bank-mcp-MIT.txt.

Changes: Python pure functions instead of SQL/fetch, exact Decimal instead of float, explicit currency/status/date provenance, bounded input/output, generic refusal, fixed supplied-row scope. No SQLAlchemy, DB, cron, network, regex category rules, cashflow prediction or upstream token/config handling copied. Append this attribution to accumulated THIRD_PARTY_NOTICES before publication, do not replace previous notices. Full dependency/source review is limited to these extracted patterns and retained licenses, not the whole upstream project.

## Tests

26 synthetic unit tests, normal and optimized Python. Covers exact arithmetic under a hostile ambient decimal precision, multi-currency/pending separation, category precedence, refunds, incomplete/duplicate scope, unknown/inferred dates, Unicode casefold, inclusive date bounds, pagination truncation, immutable source rows, bounded input, maximum precision, invalid amounts/currency/status/provenance/categories and generic errors. No real account, bank, Windows integration or complete history proven.

Pending-to-booked boundary: this module does not detect that a pending row and a later booked row describe the same underlying transaction. They remain separate status groups. The caller must choose a known non-overlapping selection for the intended report and must not combine both totals as distinct charges. Neither equivalent identities nor complete history are proven by these tests.
