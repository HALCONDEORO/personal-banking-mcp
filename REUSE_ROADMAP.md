# Reuse roadmap for the personal banking MCP

19 November 2026. Target: the user's Windows laptop. No server deployment, public callback, VM, payments or persistent financial database. This is a source/review inventory, not a claim of live Revolut compatibility.

| Upstream | Pin | License read | Useful function or pattern | Proposed package | Decision and limits |
|---|---|---|---|---|---|
| borgels/mcp-server-enablebanking | 86fc2ed20e898eb81db5b6de3d17cc28b05acf4d | Apache-2.0 | Callback, policy, registry and redirect negative tests | Admin transport/callback hardening tests | Reuse selected cases after code review. Do not copy corporate account routing, broad gateway or error-body text into public errors. Preserve Apache notices for copied/adapted material. |
| Beennnn/openbanking-mcp | e6ef5fc6298d4a9064ae96ceada49b4a6c009195 | MIT | Network-free doctor, small provider contract, age-aware reads | Offline doctor and provider interface | Good fit for quota-free readiness checks. Do not copy hand-rolled RSA, launchd automation, live consent code or brief side effects. |
| elcukro/bank-mcp | c6abad503b1ecec47e80108ef8d0c614da0f4de5 | MIT | Provider interface, mock provider, read filters | Provider-neutral fixtures, search tests | Reuse narrow interfaces and mock cases. Do not adopt clipboard-based consent handling or assume README consent durations. |
| guille-near/openbanking-mcp | d61e3ad67b60aa848d96887fd4d06dc3fefbd749 | MIT | Mapper tests, pure spending summaries, categories, subscription/anomaly tests, separate sync/read layers | Fixture analytics, deterministic read-only search and summaries | Start with pure functions on supplied synthetic transactions. Exact Decimal strings, explicit currency separation, pending/booked handling, no double counting, no claims of complete history. SQLite/cron/cache not included. |
| Algiras/enable-banking-mcp | d23eadb65ff1e2d619537d7e58e9e3aa18ff3f5f | MIT | Read-only UI examples might inform presentation | Optional future local viewer | Do not integrate server as-is: payment, secret/config and consent tools share its surface. No payment or secret-capture code enters this MCP. |
| HALCONDEORO/tesco-ie-grocery-mcp | 08db94c5230ab74d9a573415442e22a5961e5c69 | MIT | Serial queue, injected clock, provenance and doctor patterns | Multi-call load budget and offline diagnostics | Provenance and doctor already adapted. Queue needs bounded waiting/count/elapsed time and no retries. Do not copy error-message interpolation or anti-bot behavior. |
| HALCONDEORO/chemical-cabinet | a0ca143f206f7d92aa9b2676de00e729c282442e | MIT | CSV formula neutralization and negative boundary tests | Optional user-requested export | Export only explicit reviewed fields, neutralize spreadsheet formulas, preserve original values internally. No financial storage or automatic export destination. |

## Delivery order

1. Complete remaining reviewed local prototypes: admin HTTP, Windows design revision and synthetic integration suite. Preserve isolation between admin linking and read-only MCP tools.
2. Offline doctor using local configuration metadata only. Do not run bank probes to tell the user whether setup is present.
3. Bounded multi-call queue and shared request budget, injected monotonic clock, no automatic retries or rate-limit circumvention.
4. Pure fixture analytics: text/date/amount search, per-currency inflow/outflow summaries and category grouping. No currency conversion or float money.
5. Explainable recurring-charge candidates and unusual-charge candidates, explicitly uncertain, never predicted debits presented as obligations.
6. Optional file export with formula neutralization, explicit user-selected fields and destination, no silent persistent cache.

Each package needs pinned upstream source, copied license and modification notice when material is adapted, exact remote source readback, independent review and exact-head CI. No whole-repository import by reputation or a license badge. No GPL material.

## Sources inspected

- https://github.com/borgels/mcp-server-enablebanking
- https://github.com/Beennnn/openbanking-mcp
- https://github.com/elcukro/bank-mcp
- https://github.com/guille-near/openbanking-mcp
- https://github.com/Algiras/enable-banking-mcp

The five repositories above were fetched from their own pages and cloned read-only; license files and selected implementation/tests were read. No upstream install scripts were run. Pins describe the inspected trees, not an ongoing promise about future revisions.

## Known gaps

No inspected third-party project has yet supplied verified real-account Revolut evidence in this review. Enable Banking's official integration listing supports personal Revolut, but exact callback acceptance remains unresolved. A pending human-support request is not permission to register Production.

The POSIX store cannot be treated as a Windows secret store. Windows credentials/certificate handling, the local TLS relay, browser handoff and removal procedure remain separate release gates. The previous SSH-to-server topology is superseded by the user's laptop choice and must not survive as the default instructions.

Independent review confirmed the seven cloned repository pins and top-level licenses only. Function choices above are an implementation roadmap, not a full upstream code or dependency audit. Each extraction still requires its own source and transitive-license review.
