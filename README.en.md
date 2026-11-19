# personal-banking-mcp

A local, **read-only** MCP server for personal banking, fixture-first: it works from day one against local test data (fixtures), with no real bank involved. An adapter for [Enable Banking](https://enablebanking.com/) (PSD2 aggregation) is **planned**, not implemented.

> Not affiliated with any bank. Private, personal project.

## Principles

- **Read-only.** The server cannot initiate payments, transfers or changes of any kind. There is no write path against any banking source.
- **Fixture-first.** Synthetic data is embedded in server.py. You can develop, test and read the docs without any credentials at all.
- **Local.** The server runs on your machine and talks to your MCP client (e.g. Claude Desktop) over stdio. This server only serves synthetic data; no live adapter can be enabled.
- **Keys stay out of the repo.** When the real adapter lands, credentials live in environment variables or a git-ignored `.env`. Never in code, never in the README, never in fixtures. See `CONFIGURATION.md`.

## Status

| Piece | Status |
| --- | --- |
| Documentation | In preparation |
| MCP server with fixtures | Implemented and locally tested |
| Enable Banking adapter (PSD2, read-only AIS) | Planned |

## Synthetic data usage

1. Clone the repo and follow `CONFIGURATION.md`.
2. Run against fixtures: with no environment variables or keys set, the server serves test data.
3. Point your MCP client at the command shown in `CONFIGURATION.md`.
4. Enable Banking remains planned, not available to enable in this version.

## License

MIT proposed in LICENSE. Copyright holder awaits confirmation before publication. See LICENCIAS.md and dependency-licenses.json.

## Current tool contract and limits

- `list_accounts`: two fictional accounts, no real account identifiers.
- `get_balance(account)`: synthetic decimal-string balance and currency.
- `get_transactions(account, start, end, limit=20, offset=0)`: inclusive ISO dates, at most 366 days, 1 to 100 rows, bounded offset pagination; pending and booked remain distinct.

All results carry `source: synthetic-fixtures`, `live: false` and a fixed `as_of` date. They are not current banking information. There is no connection to Revolut or any other bank, no HTTP listener and no live adapter. This is not an official product of Revolut or Enable Banking and is not financial advice.

Local execution does not make your AI client offline: your chosen MCP client may send returned data to its AI service. Transaction descriptions are untrusted data, never instructions.

## Future provider access and terms

Enable Banking restricted production permits personal, non-commercial access to an individual's own linked accounts, subject to its terms. Business accounts, access for clients and commercial or hosted multi-user use require checking the intended use with Enable Banking and a separate agreement where applicable. MIT licenses this source code, not provider access, bank data, trademarks or regulatory permission. Service-access sharing and competitive-use restrictions still apply. No provider acceptance is guaranteed.

Consent setup uses provider authorization and session-creation operations separately from account-information reads. This prototype exposes no setup, payment or account-changing tools. Expired consent must fail closed in any future adapter.

Official references checked 19 November 2026:

- [Enable Banking terms](https://enablebanking.com/terms/)
- [Own linked accounts and restricted production](https://enablebanking.com/docs/api/linked-accounts/)
- [API reference](https://enablebanking.com/docs/api/reference/)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk), MIT dependency. Its notice is in THIRD_PARTY_NOTICES.md.

Design references, no source code copied into this version: [BankMCP](https://github.com/noskillish/bankmcp/), [EU Open Banking MCP](https://github.com/cver-me/EU-Open-Banking-MCP), [Enable Banking MCP in Rust](https://github.com/Algiras/enable-banking-mcp). They are not dependencies. Dependency license metadata is in dependency-licenses.json; it does not replace license texts or distribution obligations.
