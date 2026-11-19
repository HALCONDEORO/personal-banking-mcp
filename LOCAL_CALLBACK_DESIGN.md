# Local callback design, not an operational setup yet

Status: offline protocol tested. No Enable Banking application or key is created by this package. No callback listener, tunnel, TLS installation or session exchange is implemented by this package. No bank was accessed. Production acceptance of the candidate URI is awaiting the provider's answer. Do not treat third-party localhost examples as provider approval.

## Architecture

The browser and TLS endpoint run on the owner's computer. The browser opens `https://localhost:8765/callback` after the owner completes bank authentication. A private SSH local-forward carries the request to a dedicated server-side admin listener bound only to `127.0.0.1`. This listener has no MCP entry point. The MCP process never starts consent or receives the code in a tool response.

A tunnel alone is not TLS termination. We must implement exactly one of these: a local TLS listener forwarding to the server, or a TLS listener on the server whose localhost certificate is trusted only on the owner's computer. The second means the TLS key resides on the isolated server; the first keeps that key on the computer but needs a separate local program. Select and test the complete topology before publishing commands. Never offer a tunnel command that forwards a browser HTTPS request to a plaintext listener.

## Required before setup commands

1. Provider confirmation that restricted Production accepts the exact candidate redirect and its certificate/port rules.
2. The operator selects the computer OS and a supported local TLS tool. Install instructions must match that platform; do not assume a package manager or administrative privilege.
3. The operator verifies the isolated Unix user, SSH key, host fingerprint and a loopback-only free port, and separately authorizes any host changes. This design is not a deployment instruction or evidence of a running service.
4. Review final application name, description, privacy/terms URLs and redirect before registering. URLs must resolve to reviewed published documents. No browser-generated private key goes into GitHub, chat, email or query strings.
5. Choose a local-certificate tool already supported by the owner's OS and verify its source. Explain that adding a local CA changes trust on that computer. Obtain permission before that OS trust-store change. Trust only the needed local CA and document its removal. Do not disable browser certificate checks or tell the owner to bypass warnings.

## Listener acceptance criteria

- Bind only loopback and verify that a LAN connection fails. No `0.0.0.0`, public reverse tunnel or public relay. Forwarded SSH ports are bound explicitly to loopback. Host key checking stays enabled. No agent forwarding.
- GET `/callback` only, bounded request-target/header bytes and socket timeout. Reject absolute-form requests and wrong Host, duplicate query keys, fragments, unknown parameters, invalid encoding and conflicting code/error. Never trust Host or forwarded headers to reconstruct the allowed origin.
- Start one `ConsentAttempt` immediately before the owner opens the authorization URL. State is generated in memory with 256 bits of entropy, constant-time checked, never displayed or persisted. One handler at a time; 300-second monotonic TTL; one use; error callbacks and cancellation consume the attempt.
- No request/access logging at any layer: Python handler, reverse proxy, SSH wrapper, exception logger or terminal. Do not retain full URL, query, state, code, JWT, account IDs or session bodies. Avoid shell history arguments containing sensitive data.
- Return only a constant success/failure page. `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, restrictive CSP, no assets, no analytics, no links carrying query data. Close the listener after success, cancellation or deadline. The code is not echoed in the page.
- Exchange the code through a separate fixed-origin admin transport that allows only the intended AIS endpoints. This transport is not the existing read-only GET adapter and must not widen it. Validate TLS, no redirects, no environment proxy, bounded body/time, no retry of consent/session writes. Session data goes directly to owner-only storage, never stdout/MCP.
- Revolut discovery, account linking and SCA stay with the owner. Choose the actual provider bank/country from live discovery; no hardcoded Revolut country or default account. Consent duration is explicit and separate from callback TTL.

## Offline verification

`python -m unittest -v test_admin_consent` and `python -O -m unittest -v test_admin_consent`.

These tests cover request-body construction, randomized state, replay, expiry, cancellation, mismatched state, callback errors, duplicate/unknown parameters, wrong origin, encoding and bounds. They do not verify browser TLS, SSH topology, provider redirect acceptance, local OS trust, a real user flow or a bank session. Those are release gates, not work declared done.
