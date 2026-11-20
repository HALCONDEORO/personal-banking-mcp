# Configuration without exposing credentials

Current release: synthetic fixtures only. The MCP server does not read banking environment variables, load an application key or offer a live mode. No configuration flag can turn the demo into a working bank connector.

## Run the fixture demo

Follow [the README quick start](README.md#quick-start). Do not set bank credentials. The five tools must retain the synthetic source, `live: false` and fixed fixture date. A missing or failed fixture is an error, not permission to switch to real data.

Use a local stdio MCP client with absolute Python/server paths as the README describes. No account, key, provider application or cloud service is needed. The client may send tool results to its AI provider; local execution alone does not make that client offline.

For the current personal-use registration and consent boundaries, read the
[setup readiness checklist](PERSONAL_SETUP_READINESS.md). It is preparation,
not an activation procedure.

## Planned real connection

See [final goals and release gates](ROADMAP.md). A real connection requires a separately reviewed implementation and setup, including provider eligibility, an approved application registration, a validated redirect, owner-completed linking/consent and a trusted read-only transport. The provider modules are experimental and disconnected from MCP.

For the proposed Windows design, the private signing key should remain in the operator's own supported Windows key store, with a nonexportable policy. Only a public certificate would be registered. This design still requires Windows testing, exact permissions, failure cleanup, secure integration and recovery proof. It is not implemented by a `.env` file or a reference to an exported PEM key. Do not create or export a private key by following older configuration examples.

Application ID, bank country, consent/session bindings and public-certificate identity belong in private reviewed local configuration, not MCP arguments, public source or screenshots. Actual configuration names and supported versions must be fixed by the implementation before use. Earlier proposed environment-variable names are not a supported interface.

## Secret-handling rules

- Never put key contents, JWTs, bank passwords, consent codes or session tokens in the repository or MCP client JSON.
- Do not print private configuration, full callback URLs, bank response bodies or financial identifiers in logs.
- Keep operational state outside the source tree with verified owner-only access. A gitignore entry is an extra guard, not a security boundary.
- Do not send real statements or credentials in issues, pull requests, tests or screenshots.
- Do not disable platform protections, change trusted roots or install dependencies merely because a sample fails. Stop and establish what is required.

## Exposure and removal

If a credential is exposed, revoke or replace it through the issuer's supported process. Removing a file from the latest commit does not remove it from history, caches, forks or logs. History cleanup is not a substitute for revocation.

Deleting local files does not revoke provider access or bank consent. A real deployment must document the supported application/consent revocation route and exact local key-container cleanup before activation. Never bulk-delete certificates or keys. Nonexportable-key recovery needs a reviewed replacement path, not a hidden private-key backup.

## Before any activation

- Final setup fields and irreversible effects shown to the operator.
- Exact public-certificate/key binding and custody tested on the target OS.
- Redirect accepted by the provider, not merely by a local listener or form field.
- Current provider terms and account eligibility checked.
- Owner completes bank consent and SCA through the supported flow.
- Live reads authorized and restricted to the intended accounts.
- Storage, logs, revocation, recovery and limits reviewed and documented.

This document is a boundary and preparation guide, not a completed connection procedure. No real-bank compatibility or production-readiness claim follows from it.
