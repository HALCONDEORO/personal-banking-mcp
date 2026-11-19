# Session boundary notes

Offline code only. No session is created, refreshed, revoked or fetched. No HTTP client or MCP tool is added. Use synthetic payloads until the complete setup workflow and provider restrictions are reviewed.

`validate_created_session` is for the POST `/sessions` response, whose `accounts` is an object list. It is not for GET `/sessions/{id}`, which returns an ID list and a separate `accounts_data` field. The caller must pass the bank name, country and access end selected in the current approved authorization attempt, not copy those expected values from the response being checked. No default Revolut country, first account or automatically approved selection exists.

The helper requires personal mode, matching bank/country, future timezone-aware expiry no later than the requested end, one to50 unique canonical nonzero UUID account identifiers and a session UUID. It drops provider extras, including names, IBANs, addresses, hashes and counterparties. Unknown metadata is not interpreted as instructions.

A PrivateSession's repr is constant. `summary` includes only count/expiry and explicitly says `live_consent_status=not_verified` and `readiness=local_validation_only`. Its `transport_ids` accessor is for private internal wiring to an allowlisted read-only transport, never a public MCP result or log. It checks the expiry again. UUID shape validates format, not account ownership or current consent. Callers must separately bind this response to their current one-use callback/session exchange and verify live session status before real reads. A local time check cannot detect consent revoked at the bank.

This package does not accept or deserialize JSON itself. The future admin transport must enforce body/depth limits, duplicate-key rejection, no NaN, fixed-origin TLS, timeouts and no private data in logs before handing a dict to this validator. Do not feed it unbounded untrusted Python objects. Exception handlers must not enable traceback local-variable capture. Python object fields and returned private tuples are not encryption or memory erasure.

## Verification

`python -m unittest -v test_provider_session` and its `python -O` equivalent. Sixteen offline tests cover expiry/binding/UUIDs/duplicates/bounds, private repr and summary, generic full tracebacks and input immutability. These tests do not establish provider acceptance, account ownership or a working bank flow.

## Sources

- Official POST sessions versus GET session schemas: https://enablebanking.com/docs/api/reference/
- MIT interface shapes: https://github.com/noskillish/bankmcp/blob/12b2a8a30b7c8b7d46dd1d0dd44cebde2f89be6a/src/enablebanking.ts
