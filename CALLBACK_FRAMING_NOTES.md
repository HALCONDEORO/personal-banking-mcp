# Callback relay framing

Original MIT project code. Uses Python standard-library re and bytes only. No new third-party runtime dependency. Integration tests require the separately attributed Apache-2.0 `admin_consent.py` package. Preserve that file's Apache license and notices; this package does not relicense it or bundle a different copy.

## Contract

This is an offline parser/builder for a deliberately tiny internal protocol between a future Windows TLS relay and a backend callback listener. It is not a general browser HTTP parser. It opens no sockets, installs no certificates, starts no listener and contacts no provider. It is not a complete end-to-end banking or TLS test.

The Windows relay must first validate its browser-side request and then REBUILD a request containing only a GET origin-form `/callback?...` target, HTTP/1.1, fixed `Host: 127.0.0.1:8766` and `Connection: close`, in that order. Do not transparently forward browser headers, Content-Length, Transfer-Encoding, cookies, authorization or forwarding headers. The tiny backend protocol intentionally rejects additional headers rather than supporting general HTTP.

The parser caps total request bytes12288 and target8192, requires ASCII CRLF framing, rejects bodies/pipelining/control characters/absolute URLs/path alternatives/invalid percent syntax, and reconstructs the browser callback origin from a constant, never Host input. The resulting URL is private and must be passed immediately to ConsentAttempt for strict query/state/TTL/replay validation. A syntactically valid request is not an authenticated callback. Host is not authentication; the eventual listener must still bind only loopback behind a reviewed owner-authenticated SSH tunnel.

Socket read limits, handshake/read deadlines, connection caps, one-handler serialization, process shutdown at attempt expiry and constant local logging policy must be implemented at the listener boundary. This pure parser does not enforce those lifecycle limits. The future TLS relay needs its own browser-facing bounded HTTP parser and source/Host/path checks. Do not claim this parser secures unimplemented networking.

Response bytes are constant plain text with no-store, no-referrer, CSP and nosniff headers. They never contain provider content, state, code or private URL. A200 response says only that the callback was locally validated; it explicitly does not confirm a bank session. No response templating or remote assets exist.

## Tests

`python -m unittest -v test_callback_framing test_admin_consent` and `python -O` equivalent. Twelve new tests plus20 AIS tests cover strict header/method/Host/body/target/size/type failures, full generic tracebacks, response length/security headers, deterministic2000-input malformed-byte fuzzing, and a synthetic in-process private relay->state validation->replay rejection flow. No OS trust store, real HTTP socket, Windows UI, SSH connection, provider request, bank linking or SCA is exercised.
