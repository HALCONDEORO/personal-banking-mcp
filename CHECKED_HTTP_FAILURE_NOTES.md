# Second-page HTTP composition failure tests

Original MIT tests, copyright 2026 Marco Antonio Tevar Asensio. No new dependency, runtime, workflow or provider configuration changes.

`test_checked_read_http_failures.py` joins the existing pager, CheckedSessionRead and ReadOnlyHTTP with httpx.MockTransport. It never constructs a real network transport. The synthetic session, account, token, bank and transaction are not real credentials or bank data.

## Eight methods

- Positive control: two session checks and two account GETs produce one synthetic debit of EUR 12.34, with pagination complete but history_complete and live both false.
- Second account response redirects: return unexpected_status, no follow and no retry.
- Second account response throttles: return rate_limited, no retry.
- Malformed second-page JSON: invalid_response.
- Duplicate second-page JSON keys: invalid_response.
- Provider validity expires exactly during the second account response: transport_failure, neither page returned.
- Local session expires exactly during the second account response: transport_failure, neither page returned.
- Caller cancellation while the second account handler is blocked: CancelledError reaches the caller and the handler observes cancellation; no retry.

All negative cases first send the same valid nonempty first page used by the positive control. Reaching the second account GET establishes that the pager accepted the first page. Every test asserts exactly the expected four request paths, four token-supplier calls, GET-only methods, fixed provider host and unchanged continuation key. Failure assertions inspect the public exception for the expected safe code, absent row/error markers and no displayed chained context. They do not claim that Python exception objects retain no internal frames or private state. The negative outcome is an exception rather than a partial result, not proof of secure memory erasure.

## Evidence boundary

Local full-suite results on base c8dccfdac38d2437f335d176c80a253f437aebb4 plus this two-file candidate: 359 Python unittest methods, normal and -O; Node 9/9 properties, 55/55 fuzz and 58/58 e2e.

The tests cover existing behavior and exposed no runtime defect. Initial authoring failures were an incorrect mock response constructor (buffered content rather than raw ByteStream) and an overly strict assertion that direct status errors must set a context-suppression flag even when no context exists. Both were corrected in the tests, without changing product code or the intended guarantees.

Cancellation is coordinated with asyncio Events, not a sleep or a simulated deadline. A one-second wait bounds the test's event rendezvous only; it is not a provider timing guarantee. Frozen wall-clock changes model expiry at the response boundary, not actual time passing or bank revocation propagation.

No sockets, DNS, TLS, redirect destination request, real provider, JWT signing, Windows, signer, registration, keys, consent, storage or MCP activation is exercised. The test does not prove real network cancellation, HTTP connection cleanup, unread error-body behavior, cross-process concurrency, cancellation-suppressing transports or live-bank compatibility. Those require separate evidence. No new activation authority is implied.
