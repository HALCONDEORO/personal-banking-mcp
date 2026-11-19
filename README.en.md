# Personal Banking MCP

Local, read-only personal-finance tools over the Model Context Protocol (MCP). Start with invented data, without a bank account, API key or cloud service.

**This is a synthetic-data prototype, not a working Revolut connector.** Enable Banking support is planned. The current MCP server cannot connect to any bank, initiate a payment or change an account. Do not present its output as current banking information.

[Español](README.md) · [English](README.en.md) · [Provider support](docs/PROVIDERS.md) · [Tests](docs/TESTING.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

## Install and try it

Requirements: Python 3.10 or newer and pip. Download or clone this repository, then run these commands from its root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m unittest -v
python test_server.py --demo
```

Windows PowerShell: use `py -3 -m venv .venv` and `.venv\Scripts\Activate.ps1` instead of the first two commands.

The demo starts a real local MCP client/server session over stdio, calls all five read-only tools, tries requests that must fail, and prints invented results. It does not ask for banking credentials or send requests to a bank. Install dependencies only in the virtual environment. Their versions are pinned; requirements.txt is not an artifact-hash lockfile.

## Connect an MCP client

Use an MCP client that supports local stdio servers. Example configuration, replace both absolute paths with your checkout location:

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

On Windows, point `command` to the environment's `Scripts/python.exe`; use JSON-compatible paths such as `C:/path/personal-banking-mcp/.venv/Scripts/python.exe`. Your client may use a different configuration-file location or schema. No environment variables, tokens or bank account identifiers are required. Running `python server.py` directly waits for an MCP client, not interactive terminal input. This server does not open an HTTP listener.

Local execution does not mean your AI client is offline. The client may send returned data to its AI service. Review its privacy settings before connecting any future real-data adapter.

## Tools and synthetic examples

| Tool | Arguments | Result |
| --- | --- | --- |
| `list_accounts` | None | Two fictional accounts, excluding balances |
| `get_balance` | `account` | Decimal-string amount and currency |
| `get_transactions` | `account`, `start`, `end`, optional `limit` and `offset` | Filtered synthetic movements with bounded pagination |

Example tool arguments:

```json
{"account":"demo-eur","start":"2026-01-01","end":"2026-01-05","limit":2,"offset":0}
```

Every response includes `source: synthetic-fixtures`, `live: false` and the fixed `as_of: 2026-01-05`. Account IDs and descriptions are invented. Amounts are decimal strings, not binary floats; pending and booked movements remain distinct. Transaction dates are inclusive ISO `YYYY-MM-DD`, ordered, with at most 366 inclusive days. `limit` is an integer from 1 to 100, default 20; `offset` is an integer from 0 to 10000, default 0. Booleans, strings and floats are not accepted for pagination. Follow `next_offset` until null; `complete` describes this synthetic result only, never full bank-history availability.

## Provider support and configuration

See [the provider matrix](docs/PROVIDERS.md). There is no live provider available in this release and no real-bank mode to enable. Banking environment variables are currently ignored by the server. [CONFIGURATION.md](CONFIGURATION.md) and [CONFIGURACION.md](CONFIGURACION.md) describe future setup ideas, not an implemented connection flow. Never supply credentials in a GitHub issue, pull request or client example.

If a PR includes `provider_normalize.py` or `provider_pager.py`, these are isolated experiments over synthetic responses and injected transports. They are not MCP tools, do not implement an HTTP transport and do not connect a bank. Read their source limitations before reuse.

## Boundaries

- No payments, transfers, trading, currency conversion, card changes or account-changing tools.
- No authorization or consent-creation tools. A future provider setup needs a separately reviewed, human-operated flow.
- No telemetry, persistent financial cache, background polling or HTTP service in the current server.
- Descriptions and other provider text are untrusted data, never instructions or proof of approval.
- Tool annotations describe intent; code boundaries and tests matter. This prototype is not a security audit or production authorization system.
- Provider access, bank coverage and use rights must be checked independently. Source-code availability does not grant service access.

## Develop

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [the test guide](docs/TESTING.md). Work in a branch, open a pull request, and wait for independent review and checks at the exact head before merging. Do not introduce live-bank tests or secrets into CI.

## License and attribution

Original code: MIT, copyright 2026 Marco Antonio Tevar Asensio. See LICENSE. Third-party packages retain their own licenses. The official Python MCP SDK is an installed MIT dependency, not vendored code; its notice is preserved in THIRD_PARTY_NOTICES.md. See LICENCIAS.md and dependency-licenses.json. Adding JavaScript test dependencies requires maintaining their license inventory too.

Design references, no source code copied into the original prototype: [BankMCP](https://github.com/noskillish/bankmcp/), [EU Open Banking MCP](https://github.com/cver-me/EU-Open-Banking-MCP), [Enable Banking MCP in Rust](https://github.com/Algiras/enable-banking-mcp).

Not affiliated with, endorsed by or an official product of Revolut or Enable Banking. Not financial advice. MIT covers this code, not provider access, bank data, trademarks or regulatory permission.

## Fixture-only search and summary

`search_transactions(account, start, end, query="", limit=50)` performs bounded literal description search. `summarize_transactions(account, start, end)` reports exact decimal inflow/outflow/net, separated by currency and booked/pending status. Both retain the synthetic envelope and unknown real-history completeness. The selection is projected to exactly eight normalized fields, excluding account/transaction identifiers. No network, admin setup, storage or CSV tool is enabled. Query text and descriptions remain untrusted data. Empty selection does not prove no real transactions; pending and booked are not deduplicated or combined. Dates use the same inclusive, at most366day fixture contract.

The projection fixes currency_known=True and date_source=transaction_date ONLY for the closed EUR/GBP fixtures whose dates have that meaning. A real adapter must preserve unknown currency and actual date/fallback provenance instead of copying these assumptions.
