# Third-party notices

## Python MCP SDK

https://github.com/modelcontextprotocol/python-sdk

Dependency, not vendored code. License text from installed mcp 1.30.0:

MIT License

Copyright (c) 2024 Anthropic, PBC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


Other installed packages retain their respective licenses. Full dependency review is required before release. No source code from the design-reference repositories was copied.


## EU Open Banking MCP money invariants

- Repository: https://github.com/cver-me/EU-Open-Banking-MCP
- Commit: `2c69f420c0dd20ecbdd65172538644f928df5cb5`
- Source: `src/lib/money.ts`
- Source URL: https://github.com/cver-me/EU-Open-Banking-MCP/blob/2c69f420c0dd20ecbdd65172538644f928df5cb5/src/lib/money.ts
- License: MIT, original in `LICENSES/EU-Open-Banking-MCP-MIT.txt`.
- Original copyright: Copyright (c) 2026 personal-finance-eu-mcp contributors.
- Adapted file: `test_money_corpus.py`. Adapted the bounded-input, independent-decimal-context, exact decimal-string, no rounding and unsigned-zero invariants into Python regression cases. No TypeScript runtime or decimal.js dependency was imported. The existing normalizer deliberately preserves source scale and does not adopt upstream minimum minor-unit padding or its unknown-currency two-digit fallback. No totals, currency conversion or aggregation were added.
- Modifications dated 2026-11-19: Marco Antonio Tevar Asensio.

## Tesco grocery MCP observation metadata

- Repository: https://github.com/HALCONDEORO/tesco-ie-grocery-mcp
- Commit: `08db94c5230ab74d9a573415442e22a5961e5c69`
- Source: `src/provenance.mjs`
- Source URL: https://github.com/HALCONDEORO/tesco-ie-grocery-mcp/blob/08db94c5230ab74d9a573415442e22a5961e5c69/src/provenance.mjs
- License: MIT, original in `LICENSES/tesco-ie-grocery-mcp-MIT.txt`.
- Original copyright: Copyright (c) 2026 Marco Tevar.
- Adapted file: `provider_provenance.py`. Ported the observation timestamp, uncertainty and untrusted-content metadata structure to Python; removed retail market/store/pricing data and arbitrary source URLs. Added explicit synthetic/provider-response labels, timezone validation and unknown history/freshness/reconciliation status. No account IDs, cursor, authorization data or provider text enter this helper.
- Modifications dated 2026-11-19: Marco Antonio Tevar Asensio.

`provider_normalize.patch` modifies existing project code and retains its project MIT license. `patch-base.json` records the exact observed main revision. Apply the minimal patch only after verifying its base/context; do not replace newer normalizer changes blindly. The full patched normalizer is included for reviewer execution, not as authority to overwrite remote changes.

## Enable Banking API samples

- Upstream repository: https://github.com/enablebanking/enablebanking-api-samples
- Pinned commit: `7a16788840c42b63c305652f8ea29ab69207db25`
- Source: `python_example/account_information.py`
- License: Apache License 2.0, reproduced in `LICENSES/Apache-2.0.txt`.
- Upstream copyright attribution: Enable Banking API samples contributors. The source file has no explicit copyright notice; the upstream LICENSE contains only the standard appendix placeholder, not a claimed dated copyright. No upstream NOTICE file was present in this tree.
- Source link: https://github.com/enablebanking/enablebanking-api-samples/blob/7a16788840c42b63c305652f8ea29ab69207db25/python_example/account_information.py
- Adapted file: `admin_consent.py`, under Apache-2.0, not relicensed as MIT.
- Modifications dated 2026-11-19, copyright Marco Antonio Tevar Asensio: extract the AIS request-body and callback sequence into an offline admin-only building block; remove printing, requests, credentials, JWT generation, live network, automatic first-account selection and unrestricted data output. Require personal mode, bank/country selection, a fixed loopback redirect, cryptographic one-use state, constant-time state comparison, strict callback shape and monotonic five-minute deadline. Bound access duration independently. No payment code was used.

The test module is original project code. The repository's existing MIT license is not replaced by this package. Apache obligations apply to the adapted file and any downstream modifications of it.

Lifecycle additions dated 2026-11-19: `remaining_seconds` and `closed` expose only attempt lifetime and closure, never state or code. These modifications to `admin_consent.py` remain Apache-2.0.

## Studio Saelix Finance paths

- Upstream: https://github.com/Studio-Saelix/finance-mcp
- Pinned commit: `044401cea1a141e7f40e388528b3beb536b6c31b`
- Source: `src/plaid_mcp/paths.py`
- Source URL: https://github.com/Studio-Saelix/finance-mcp/blob/044401cea1a141e7f40e388528b3beb536b6c31b/src/plaid_mcp/paths.py
- License: MIT, full original text in `LICENSES/Studio-Saelix-MIT.txt`.
- Original copyright: Copyright (c) 2026 plaid-mcp contributors.
- Adapted file: `private_store.py`, MIT.
- Modifications, 2026-11-19, copyright Marco Antonio Tevar Asensio: preserve owner-only directory/file checks from the upstream paths design, but replace check-then-open path operations with POSIX descriptor-relative traversal and O_NOFOLLOW at every component. Reject insecure permissions rather than silently changing existing files. Add hardlink rejection, regular-file checks, bounded reads/writes, private exclusive temporary files, atomic replacement, fsync and cleanup. Remove application-specific paths, XDG defaults and value-bearing exceptions. No Plaid credentials, database or other upstream application modules are imported.

Tests and integration notes are original project material. Keep the project's existing root MIT license; retain this upstream license and attribution with the adaptation.

## BankMCP session/account interfaces

- Repository: https://github.com/noskillish/bankmcp
- Commit: `12b2a8a30b7c8b7d46dd1d0dd44cebde2f89be6a`
- Source file: `src/enablebanking.ts`, Session and AccountResource interface shapes.
- Source URL: https://github.com/noskillish/bankmcp/blob/12b2a8a30b7c8b7d46dd1d0dd44cebde2f89be6a/src/enablebanking.ts
- License: MIT, original full text in `LICENSES/bankmcp-MIT.txt`.
- Original copyright: Copyright (c) 2026 Nils Smed.
- Adapted file: `provider_session.py`.
- Modifications dated 2026-11-19, copyright Marco Antonio Tevar Asensio: port the session/account interface shape to an offline Python validation boundary, cross-check official provider response schemas, drop all account extras, enforce personal mode and selected-bank binding, strict private UUID allowlists, bounded/unique accounts and expiry no later than the approved request. Add constant private repr, explicit internal ID handoff and a summary that does not claim current consent. No upstream networking, JWT caching, OAuth server, password handling, webhook, payment, attestation or session mutation code is used.

The tests and notes are original project material under the project's MIT license. Keep this attribution and upstream MIT license with the adapted module. The project root license is not replaced.

## Tesco grocery MCP doctor pattern

- Repository: https://github.com/HALCONDEORO/tesco-ie-grocery-mcp
- Commit: `08db94c5230ab74d9a573415442e22a5961e5c69`
- Source: `src/doctor.mjs`
- Source URL: https://github.com/HALCONDEORO/tesco-ie-grocery-mcp/blob/08db94c5230ab74d9a573415442e22a5961e5c69/src/doctor.mjs
- Original copyright: Copyright (c) 2026 Marco Tevar.
- License: MIT, original full text in `LICENSES/tesco-ie-grocery-mcp-MIT.txt`.
- Adapted file: `provider_doctor.py`.
- Modifications dated 2026-11-19, copyright Marco Antonio Tevar Asensio: adapt the injected probe and fixed safe verdict table from retail-page diagnostics to a private read-only provider status probe. Remove all URLs, scraping, page parsing, error-message interpolation and automatic live fetch behavior. Add total cooperative timeout with late-success rejection, no retry, typed result/status validation, explicit incomplete-readiness/history labels and no private exception exposure. Do not adopt anti-bot code, bank mutation or automatic consent handling.

Tests and notes are original project material under the project's MIT license. The existing root project license is not replaced.


## provider_load.py queue adaptation

The serial queue, interval and injected-clock pattern in provider_load.py is adapted from src/load-control.mjs at HALCONDEORO/tesco-ie-grocery-mcp, commit08db94c5230ab74d9a573415442e22a5961e5c69, MIT, Copyright(c)2026MarcoTevar.

Pinned source: https://raw.githubusercontent.com/HALCONDEORO/tesco-ie-grocery-mcp/08db94c5230ab74d9a573415442e22a5961e5c69/src/load-control.mjs

Changes: rewritten in Python asyncio, bounded active/waiting job count, per-workflow call slots and monotonic deadline, cancellation propagation, generic errors and synthetic tests. No upstream challenge detection, fetch API or error-message interpolation is included. The full MIT license is retained in LICENSES/tesco-ie-grocery-mcp-MIT.txt. Prior attributions are unchanged. This adaptation does not establish a bank quota policy.


## transaction_analytics.py category and search adaptation

Category precedence and grouped summaries adapt guille-near/openbanking-mcp commit d61e3ad67b60aa848d96887fd4d06dc3fefbd749, MIT, Copyright(c)2026 Guille Pérez. Pinned sources:
https://raw.githubusercontent.com/guille-near/openbanking-mcp/d61e3ad67b60aa848d96887fd4d06dc3fefbd749/src/finmcp/analytics/categories.py
https://raw.githubusercontent.com/guille-near/openbanking-mcp/d61e3ad67b60aa848d96887fd4d06dc3fefbd749/src/finmcp/analytics/summaries.py
Full text: LICENSES/guille-near-openbanking-MIT.txt.

Literal text-search pattern adapts elcukro/bank-mcp commit c6abad503b1ecec47e80108ef8d0c614da0f4de5, MIT, Copyright(c)2026 bank-mcp contributors. Pinned source:
https://raw.githubusercontent.com/elcukro/bank-mcp/c6abad503b1ecec47e80108ef8d0c614da0f4de5/src/tools/search-transactions.ts
Full text: LICENSES/elcukro-bank-mcp-MIT.txt.

Changes: Python pure bounded supplied-row functions, exact Decimal strings instead of float, explicit currency/status/date provenance and incomplete-history scope. No SQL, DB, fetch, cron, automatic categories or token/config handling. Previous notices and license files remain unchanged.
