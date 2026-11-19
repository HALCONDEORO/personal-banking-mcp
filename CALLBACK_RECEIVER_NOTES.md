# Loopback callback receiver prototype

This is an explicit-start private backend prototype. Imports and construction do not open ports. `await receiver.start()` opens a real plaintext TCP listener ONLY on `127.0.0.1`. It is not the Windows HTTPS listener and must never be bound publicly or used as a browser HTTPS endpoint. No provider calls, session creation, key storage, SSH or OS trust changes occur.

Default backend port8766. Port0 is supported only as an ordinary ephemeral development/test listener. The framing Host remains the fixed internal protocol identity, not a security claim or network destination supplied by the client. The full Windows TLS/SSH relay is still unimplemented/unverified. This receiver is not wired into MCP, not a daemon or production deployment and has no CLI/autostart.

## Lifecycle

Create a fresh ConsentAttempt, then a CallbackReceiver for that attempt. Start it explicitly and await its private result in a try/finally that closes it. The receiver starts its own expiry task at start, even if the caller forgets to await the result. Shutdown uses the lesser of the receiver cap (maximum300s) and the attempt's remaining monotonic lifetime, so starting a listener later does not extend an existing attempt.

One request handler at a time. A busy second connection is rejected, not queued. At most8 accepted TCP connections per receiver, including invalid requests; exhausting that budget stops the listener and requires a fresh approved setup attempt. Each request has a total read deadline (maximum2s), byte cap and bounded response drain/close. The relay must half-close its sending side after the complete rebuilt request, then read the response. Reading through EOF ensures appended bodies or pipelined requests cannot be ignored. This is a tiny custom loopback relay protocol, not general browser HTTP.

Stop accepting immediately on a locally validated callback, a terminal attempt error/expiry, or connection-budget exhaustion. The successful response never includes code/state and explicitly says the bank session is not confirmed. The private result is only a POST/sessions body for the separate reviewed admin transport. The backend must never exchange it through MCP, print it, place it in a URL or persist it in a log. Denial/replay/expired requests cannot return a private result. Cancellation and close invalidate the attempt. Do not restart a receiver object or reuse the attempt after shutdown.

Localhost is not authentication. Other local processes may reach this port; the random state/strict deadline prevents unauthorized acceptance, but local denial of service remains possible. Same-UID hostile processes and compromised hosts are outside the boundary. No port reservation or claim of sole ownership exists until bind succeeds. No automatic retry or new consent is initiated after failure.

## Dependencies and attribution

The receiver and tests are original MIT code. They use the separately reviewed MIT callback_framing module and Apache-2.0 admin_consent module. An updated copy of admin_consent adds only lifecycle properties `closed` and `remaining_seconds`; its original Apache attribution/license remain intact. Merge these properties without overwriting newer reviewed code or notices. Keep `LICENSES/Apache-2.0.txt` and accumulated THIRD_PARTY_NOTICES.

## Actual test evidence

Fourteen new tests use real ephemeral IPv4 loopback TCP sockets and synthetic state/code bytes. Combined receiver+framing+AIS suite46 tests passes normal and optimized Python. Tests include loopback bind, success with private result/constant response, socket closed after success, malformed then valid, body/pipelining, slow incomplete request deadline, independent lifetime shutdown without a wait call, generic expiry, cancellation,8-connection budget, oversize and no object restart. These are not Windows, TLS, SSH, provider, live bank or SCA tests. No such readiness is claimed.

Connection-limit qualification: the maximum-eight budget counts connections delivered to application handlers, not a hard kernel-level TCP acceptance or backlog limit. Loopback binding does not authenticate the caller. Local processes can exhaust this budget and cause denial of service; no claim of local DoS resistance is made.
