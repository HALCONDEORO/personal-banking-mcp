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
