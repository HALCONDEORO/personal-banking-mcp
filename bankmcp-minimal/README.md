# Minimal BankMCP adoption, audit branch

This is a reduced, modified source fork of the Enable Banking read client and MCP
boundary pattern from [noskillish/bankmcp](https://github.com/noskillish/bankmcp),
pinned to `12b2a8a30b7c8b7d46dd1d0dd44cebde2f89be6a`.
Upstream copyright: Nils Smed, 2026. The full MIT notice is in
[LICENSE.upstream](LICENSE.upstream). Preserve it in distributions.
This is not an upstream release and is not endorsed by its author.

## Adoption decision

Use the existing AIS approach, not another custom Windows TLS/IPC bridge.
The previous Python MCP and Windows experiments remain unchanged as historical
fixtures and tests. They are not the production entry point for this branch.
Do not delete or archive that history before an authorized real trial succeeds.

BankMCP is the smaller fit for lists, balances and transactions. Fine adds a local
transaction database, categorization, budgets, FX and scheduled services. Those
may be useful later but are not needed for this first bounded read.

This branch is an **audit candidate**, not a working owner installation. There is
no production executable, registration, authorization or session import command.
No bank account or real credentials were used to build or test it.

## What was retained and changed

- `ais.mjs` adapts the upstream RS256 JWT shape, typed client endpoint selection,
  and balance/transaction resource model. It uses five-minute app JWTs rather
  than the upstream one-hour cache. This is unrelated to bank consent lifetime.
- `mcp.mjs` retains the `McpServer` factory/registration pattern, reduced to exactly
  `list_accounts`, `get_balance`, `get_transactions`. No consent or payment tool.
- `store.mjs` is a new AES-256-GCM authenticated store, atomic file replacement,
  fsync and exclusive lifetime lock. It stores account/session metadata and quota,
  not transaction or balance responses. The cipher key must be supplied by an
  owner-side OS-protected integration that **does not exist here yet**.
- New tests use invented state and injected transport only. JWT tests generate
  disposable RSA test keys in memory and never print or save them.

Upstream hosted HTTP/OAuth, attestation, key-upload setup, automatic registration,
callbacks, certificate generation, watchers, webhooks, financial analytics and
business-customer choice are **not included**. Dependencies already locked by the
parent repository are used; no upstream install script or installer was run.

## Safety boundary

The sole production transport is native HTTPS GET to
`https://api.enablebanking.com/accounts/<approved-id>/{balances|transactions}`.
No redirects, user-selected origins, generic URL tool, POST, DELETE, payment
endpoint, auto-pagination, retry, polling or presence override is implemented.
An injected transport is a code-level synthetic test seam, not a tool argument
or configuration switch. Changing code can change this boundary; it is not an
operating-system network firewall.

The list tool reads authorized local metadata and labels it non-live. Each bank
page costs one durable slot, reserved before network, at most four per rolling
24 hours per approved account and endpoint. Failed pages count. Consent expiry,
revocation, malformed state, clock rollback, store failure or a failed/ambiguous
request fails closed. A request first writes a persistent stop latch, never cleared on disk. The same process may resume only after a valid response
and a fully durable final update, including directory fsync. A failed final
write or process restart leaves it stopped, even after a successful read.
This conservative audit candidate therefore needs owner recovery after restart.
There is no automatic stop/lock/quota reset or renewal operation.

The transport has a ten-second total deadline and one-MiB response cap. No raw
provider error body is returned. Money strings are kept unchanged, without
floating-point conversion. Descriptions in successful provider data remain
untrusted text. Returned pages are not persisted by this adapter; the MCP client
may retain its conversation, which requires its own disclosure/approval.

This does **not** make every AIS call a consent check. Local expiry is checked;
bank-side revocation can happen sooner and will be discovered on a failed read.
There is no financial cache that can conceal that failure. A successfully listed
local account is not evidence of current bank access.

## Deliberate remaining gates

1. Independent line-by-line review of all retained/new source and tests, then CI
   at the exact published tree. Synthetic tests are not a production audit.
2. OS-backed cipher-key/signing-key custody and an owner-only startup path. No
   persistent secret is collected through MCP, environment variables or chat.
   AES at rest alone is not key custody or protection from the same logged-in user.
3. Windows ACL/key integration is absent. `EncryptedStore` explicitly refuses
   Windows rather than pretending POSIX modes enforce a Windows boundary.
   Unix owner-only files are checked; this is not protection against malicious
   same-user processes, filesystem races, snapshots or restored old quota files.
4. Owner-only consent/renewal/revocation procedure with exact redirect validation,
   one-use state, actual ASPSP maximum, consent expiry and selected accounts.
   None is exposed to an assistant as a tool. Sessions cannot be minted here.
5. Preserve quota across consent renewal, account replacement and restart, and
   make recovery from a stale lock/stop a reviewed owner procedure. This version
   intentionally does not provide recovery or renewal, nor a migration importer.
6. Target-device verification, chosen history/page budget, retention approval,
   vendor terms and explicit approval before a real read. First failure stops.

No claim of permanent access, Revolut compatibility, laptop qualification,
production readiness or successful real consent follows from this branch.

## Synthetic verification

From the repository root after its existing locked dependencies are installed:

```
node --test bankmcp-minimal/test/*.test.mjs
```

This uses no live network. It covers tool exclusion, path/destination policy,
expiry/revocation/clock gates, one-page bounds, quota persistence and boundaries,
stop-on-failure, concurrency, JWT signature, authenticated encryption, corruption,
wrong keys, permissions and a real in-memory MCP client/server exchange.
