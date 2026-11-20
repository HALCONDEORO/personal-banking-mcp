# Checked session reads: isolated preparation

This module is not an MCP tool, registration client or live integration. It has
no network default, secret reader, signer, POST, DELETE, consent renewal or retry.
Tests inject only synthetic responses. No bank was connected or called.

## Gap addressed

A locally unexpired `PrivateSession` cannot establish that provider consent is
still authorized. `CheckedSessionRead` composes a fixed `GET /sessions/{id}` check
immediately before each allowed account details/balances/transactions request.
It accepts only `AUTHORIZED`, personal PSU type, the explicitly selected bank
and country, future provider expiry and all locally selected account UUIDs.
Other response accounts never extend the local allowlist. Cancelled, closed,
expired, invalid, pending, returned-from-bank and revoked sessions deny the
account request. An extra `closed` timestamp also denies the request.

Both the local private session and provider response must still be unexpired.
The local expiry is not extended by a later provider expiry. No session response
is cached. A single instance serializes check/read pairs; every new account page
requires another check. This is a conservative prototype, not a verified
provider request-rate policy. A future caller must budget both calls and share
rate control at the application/account scope.

The existing read transport allowlist is extracted into a pure function without
changing its rules. It validates the account request before the session check,
so an invalid host/path/query does not lead to token retrieval or networking.
The helper bounds session JSON to 64 KiB and rejects duplicate keys/nonfinite
JSON constants. It never forwards provider error text or arbitrary exceptions.

## Limits

- The injected transport must be trusted and independently reviewed. A Python
  callable can perform arbitrary effects; this class is not a sandbox.
- The future Windows in-process signing bridge is not implemented by this work.
- No ownership can be established from the format of a UUID, country or bank
  name. The selected bank/country must come from the current provider catalogue
  and owner-approved setup. IE residence alone is not account-country evidence.
- A successful check is point-in-time information. Consent can be revoked
  between the session check and account response. This is not an atomic bank
  transaction, continuous monitor or guarantee of future authorization.
- Deadlines are cooperative asyncio deadlines. A cancellation-suppressing
  transport cannot start the second effect after a late session check, but a
  synchronously blocked event loop still requires an external supervisor.
- Lock/ordering are local to one instance/event loop, not distributed or durable.
- No balances/transactions schema, freshness, reconciliation or complete-history
  claim follows from a session check. Existing normalizers/pager remain needed.
- Registration, final certificate/form approval, provider acceptance of the
  Production loopback redirect, account linking and bank SCA remain unresolved.
  Only the account owner performs bank consent.

## Provider source

Official API reference, read 20 November 2026:
https://enablebanking.com/docs/api/reference/

`GET /sessions/{session_id}`, `GetSessionResponse` and `SessionStatus` document
accounts as UUID strings, ASPSP, access.valid_until, PSU type and state. Only
`AUTHORIZED` is described as authorized access to account information.
`RETURNED_FROM_BANK` is a separate state and is not accepted here. The session
response's additional private fields are not returned, logged or persisted by
this helper.

This source documents the protocol, not account-specific Revolut compatibility,
a Production redirect approval, authority to make a call or regulatory approval.

## Verification

17 new isolated tests cover authorized/revoked sequencing, no cache, all non-
authorized states, local/provider expiry, bank/country/PSU drift, closed state,
account-set bounds, extra-account non-adoption, malformed response/JSON, denied
requests before effects, late/suppressed cancellation, errors without private
context, concurrent pair ordering and no input mutation.

329 tests pass under normal Python and `-O` on the exact local candidate. This
is synthetic integration evidence only. Independent review and exact remote-
head CI are required before any merge. Runtime activation is not included.

The provider expiry returned by the session check is retained and checked again
immediately before the account effect and before returning its result. Two
transition tests cover that independent bound. An integration test runs the
actual simulated pager through the wrapper, revokes before the second page,
and verifies no partial success or second account effect escapes.
