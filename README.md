<p align="center"><img src="banner.svg" alt="Personal Banking MCP: local, read-only, synthetic data first. No bank connection or money movement." width="100%"></p>

# Personal Banking MCP

[![Fixture checks](https://github.com/HALCONDEORO/personal-banking-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/HALCONDEORO/personal-banking-mcp/actions/workflows/ci.yml)
[![Node suite](https://github.com/HALCONDEORO/personal-banking-mcp/actions/workflows/node-suite.yml/badge.svg)](https://github.com/HALCONDEORO/personal-banking-mcp/actions/workflows/node-suite.yml)

**Understand the shape of your finances before connecting a bank.** A local, read-only [Model Context Protocol](https://modelcontextprotocol.io/) server with invented accounts, exact decimal amounts and explainable transaction analysis.

**Synthetic-data prototype. No bank connection.** The current MCP server cannot connect to Revolut or any other bank, move money or change an account. The Enable Banking adapter work is experimental and disconnected from MCP. This is not a current-balance service or financial advice.

[Quick start](#quick-start) · [Five tools](#five-read-only-tools) · [Connect a client](#connect-an-mcp-client) · [Documentation](#documentation) · [Español](README.es.md)

## At a glance

| Available now | Not available |
| --- | --- |
| Local MCP session over stdio | A working live-bank connector |
| Two invented accounts, EUR and GBP | Revolut linking, credentials or SCA |
| Bounded transaction search and summaries | Payments, transfers, trading or card changes |
| Synthetic negative and integration tests | A hosted banking dashboard or public API |
| Isolated provider and analytics building blocks | Production access controls or live compatibility guarantees |

No bank account, API key or cloud service is needed for the demo. Your MCP client may still send its results to an AI service. Review that client's privacy settings separately.

## Quick start

Requires Python 3.10 or newer and pip. Clone or download the repository, then run from its root:

```sh
git clone https://github.com/HALCONDEORO/personal-banking-mcp.git
cd personal-banking-mcp
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m unittest -q
python test_server.py --demo
```

**Windows PowerShell:** replace the environment-creation and activation commands with:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

If activation is restricted by your computer's policy, use `.venv\Scripts\python.exe` directly for the remaining Python commands. Do not weaken the execution policy just to run the demo.

The demo starts a real local MCP client/server session, calls all five tools and exercises requests that must fail. The data is invented. Dependencies are version-pinned in `requirements.txt`, not locked by artifact hash. See [testing](docs/TESTING.md) for the additional Node property, fuzz and end-to-end suites.

## Five read-only tools

| Tool | Arguments | What it returns |
| --- | --- | --- |
| `list_accounts` | None | Two fictional accounts, without balances |
| `get_balance` | `account` | Decimal-string balance and currency |
| `get_transactions` | `account`, `start`, `end`, `limit=20`, `offset=0` | Bounded pages of invented movements |
| `search_transactions` | `account`, `start`, `end`, `query=""`, `limit=50` | Literal description matches within the selected fixtures |
| `summarize_transactions` | `account`, `start`, `end` | Exact decimal inflow, outflow and net, split by currency and booked/pending status |

Example transaction request:

```json
{"account":"demo-eur","start":"2026-01-01","end":"2026-01-05","limit":2,"offset":0}
```

Every response carries `source: synthetic-fixtures`, `live: false` and the fixed `as_of: 2026-01-05`. That date is fixture metadata, not freshness. Amounts are decimal strings, not binary floats. Dates are inclusive ISO dates with at most 366 days per range. Transaction pagination accepts integers only: `limit` 1 to 100, `offset` 0 to 10000. Follow `next_offset` until null. `complete` describes the selected synthetic result, never a complete real bank history.

Search and summary project exactly eight normalized fields, excluding account and transaction IDs. Pending and booked rows are not deduplicated or combined. The fixed known-currency and original-date provenance apply only to these closed EUR/GBP fixtures, not to a future bank adapter.

## Connect an MCP client

Use a client that supports local stdio servers. Replace both absolute paths:

```json
{
  "mcpServers": {
    "personal-banking-demo": {
      "command": "/absolute/path/personal-banking-mcp/.venv/bin/python",
      "args": ["/absolute/path/personal-banking-mcp/server.py"]
    }
  }
}
```

On Windows, use a JSON-compatible path such as `C:/path/personal-banking-mcp/.venv/Scripts/python.exe`. Configuration location and schema depend on your client. No bank token, environment variable or account identifier is needed. Running `python server.py` alone waits for an MCP client; it is not an interactive prompt and does not open an HTTP listener.

## Experimental building blocks

These are library/design work, **not additional connected MCP tools**:

- [Provider support](docs/PROVIDERS.md), response normalization, pagination, deadlines and request budgets, tested with injected synthetic transports.
- [Local consent design](LOCAL_CALLBACK_DESIGN.md), [private store](PRIVATE_STORE_NOTES.md) and [provider diagnostics](PROVIDER_DOCTOR_NOTES.md). No application registration, bank linking or production approval follows from their tests.
- [Pure analytics](TRANSACTION_ANALYTICS_NOTES.md), [CSV export](TRANSACTION_EXPORT_NOTES.md) and [recurring-charge candidates](RECURRING_CANDIDATES_NOTES.md). Recurrence means an unverified pattern in supplied rows, not a subscription, obligation or predicted debit. Export is not an MCP tool.

There is no live mode to switch on. Banking environment variables are ignored by the fixture server. [Configuration notes](CONFIGURATION.md) describe future setup, not an available connection flow. Provider coverage, redirect acceptance, access rights and operational readiness need separate evidence.

## Boundaries and privacy

- No payments, transfers, currency conversion, trading or account changes.
- No generic HTTP, shell or arbitrary file-reading MCP tool.
- No telemetry, persistent financial cache or background polling in the fixture server.
- Provider descriptions and transaction text are untrusted data, never instructions or approval.
- Do not submit real statements, account identifiers, credentials, private keys or session tokens to code, issues, logs or screenshots.
- A local process is not a production security boundary. Do not expose stdio through a public gateway. Tool annotations are hints, not authorization.

See [Security](SECURITY.md), [Privacy](PRIVACY.md) and [Terms](TERMS.md). Synthetic tests do not establish live compatibility, a security audit or regulatory permission.

## Documentation

| Goal | Start here |
| --- | --- |
| Reproduce tests | [Testing guide](docs/TESTING.md) |
| Understand bank availability | [Provider matrix](docs/PROVIDERS.md) |
| Review isolated HTTP work | [HTTP experiment](docs/HTTP-EXPERIMENT.md) |
| Contribute a focused change | [Contributing](CONTRIBUTING.md) |
| Report a security concern | [Security policy](SECURITY.md) |
| Check reuse and licenses | [Third-party notices](THIRD_PARTY_NOTICES.md), [license inventory](LICENCIAS.md) |
| Read in Spanish | [README.es.md](README.es.md) |

## Contributing

Small, reproducible changes with invented data are welcome. Use English for repository discussions and technical documentation. Open a focused PR, include exact test commands and limitations, and wait for independent review and green checks at the commit being merged. No live-provider tests, credentials or spending in CI. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License and acknowledgements

Original project code is MIT, copyright 2026 Marco Antonio Tevar Asensio, with the file-specific exceptions and third-party obligations in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). In particular, `admin_consent.py` remains Apache-2.0. Full texts are retained in [LICENSE](LICENSE) and [LICENSES](LICENSES). Installed dependencies retain their own licenses; inventories are in `dependency-licenses.json` and `node-dependency-licenses.json`.

Adapted source is attributed at pinned commits in the notices. Earlier design references without source copied into the original prototype include [BankMCP](https://github.com/noskillish/bankmcp/), [EU Open Banking MCP](https://github.com/cver-me/EU-Open-Banking-MCP) and [Enable Banking MCP in Rust](https://github.com/Algiras/enable-banking-mcp).

Not affiliated with or endorsed by Revolut, Enable Banking or any bank. Code licenses do not grant provider access, bank-data rights, trademark rights or regulatory permission.
