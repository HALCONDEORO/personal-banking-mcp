# Provider support

| Source | Current support | Credentials needed now | Limits |
| --- | --- | --- | --- |
| Embedded synthetic fixtures | Implemented in the three MCP tools | None | Two invented accounts; fixed January 2026 data |
| Enable Banking AIS | Planned, no live adapter | None for this release | Consent, bank eligibility, account authorization, streaming limits and safe transport remain future work |
| Revolut personal account via an aggregator | Not connected or validated | Do not provide any | Coverage depends on provider, country, account and current bank availability; no compatibility claim |
| Revolut direct API or business account | Not implemented | Do not provide any | Not part of the current personal synthetic demo |
| Other banks/providers | Not implemented | None | No generic HTTP or arbitrary provider URL tool |

A simulated normalizer or paginator is not provider support. The experimental normalizer and paginator modules operate on supplied synthetic payloads and injected transports, are not registered with MCP and do not themselves implement HTTP. `provider_pagination_complete` does not mean `history_complete`.

## Configuration today

No banking environment variables are needed or read. The source host policy uses a fixed Enable Banking host and GET read-path allowlist only as a future boundary. It is not a usable adapter. There is no bank-login flow, consent setup, private-key reader or production switch.

CONFIGURATION.md and CONFIGURACION.md list proposed future variable names. They do not activate anything. A real integration requires a separate review before collecting credentials or accessing an account. Use generic sample paths and empty placeholders in examples, never a contributor's private configuration.

## Enable Banking terms and future setup

As checked on 19 November 2026, restricted production permits personal non-commercial use of an individual's own linked accounts subject to the provider's terms. Business use, client accounts, hosted multi-user operation and commercial use need checking the intended use with Enable Banking and a separate agreement where applicable. Evaluation allowances are not an unlimited business-use grant. Access sharing and competitive-use restrictions still apply.

Consent establishment uses POST /auth and POST /sessions. Those are distinct from account-information reads and are not exposed by this MCP. A read-only data adapter must still refuse payments and account changes, constrain the owner-authorized account set, reject redirects, limit response bytes while streaming, set timeouts, bound pagination and fail closed on expired consent. Provider cursor tokens must never choose a destination host or path. No credentials or consent are supplied by this repository.

Official sources:

- https://enablebanking.com/terms/
- https://enablebanking.com/docs/api/linked-accounts/
- https://enablebanking.com/docs/api/reference/

These links describe external services whose terms and availability can change. Re-check them before implementing or using real access. Publishing MIT code does not grant rights to use a bank API, distribute bank data or provide a regulated service.

## Disconnected HTTP/JWT experiment

An experimental opt-in HTTP/JWT library is present but not wired to the MCP. No live compatibility is claimed. It uses process-wide logging-handler suppression and has no aggregate request budget. See [HTTP-EXPERIMENT.md](HTTP-EXPERIMENT.md) before considering any real use.
