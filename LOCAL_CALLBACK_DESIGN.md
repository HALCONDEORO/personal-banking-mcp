# Local callback design and release gates

Design only. The repository has isolated callback protocol, loopback HTTP receiver and admin transport prototypes tested with synthetic data. They are not a complete Windows authorization workflow. No application, key, bank consent or real session is created by these documents. The provider has not confirmed the exact localhost redirect.

## Architecture

The selected target is the owner's Windows laptop. The browser and short-lived TLS relay run there. The relay receives the candidate `https://localhost:8765/callback` and forwards only the permitted callback fields to a fixed loopback admin endpoint on the same laptop. There is no server, SSH tunnel, VM or public callback in this topology. See WINDOWS_CALLBACK_DESIGN.md for Windows-specific gaps.

The local admin workflow is separate from the read-only MCP process. MCP tools never start consent or receive callback state/codes. A loopback port is not an authenticated private channel against other local applications; local competing-process/interception risks need review before a real flow.

## Gates before setup

- Confirm provider acceptance of the exact URI, localhost versus127.0.0.1, certificate and port rules. Third-party examples are not provider approval.
- Review the Windows TLS relay and its full synthetic end-to-end tests. Do not forward HTTPS directly to a plaintext listener or disable TLS validation.
- Choose and review Windows-native protected secret/session storage. Existing POSIX storage must not be described as Windows-ready.
- Explain and obtain approval for certificate/trust-store changes before making them. Use the exact reviewed non-CA certificate and provide exact removal steps.
- Show final registration name, description, redirect and published privacy/terms documents before registering Production. Do not put keys or sensitive callback values in a repository, message, URL, process argument or tool result.

## Protocol and transport requirements

- Explicit loopback binds only; verify no LAN access. A localhost IPv6 resolution problem is not a reason to bind every interface.
- GET callback path only, bounded request target/headers and handshake/read deadlines. Reject wrong Host/origin, absolute-form requests, duplicate/unknown parameters, fragments, invalid encoding and code/error conflicts. Do not reconstruct trusted origins from forwarded headers.
- Generate 256-bit state in memory per attempt. Constant-time comparison, one use, single active handler and a monotonic300-second deadline. Cancellation, denial and error callbacks consume the attempt. Bank consent duration is separate.
- No callback/access logging in relay, handler, wrapper or exception path. Do not retain full URLs, query, codes, state, JWTs, private account IDs or session bodies.
- Constant no-store/no-referrer/CSP-restricted callback page, no external assets. Close listeners on success, cancellation, denial or expiry. Never echo provider content.
- Fixed-origin admin transport, TLS validation, no redirects or environment proxy, bounded body/time and no automatic retry of writes. Keep this separate from read-only GET transport. A timeout/cancellation may occur after a remote write has taken effect.
- Secret/session results go directly to reviewed owner-protected Windows storage, not stdout, MCP responses or screenshots. Private session IDs do not prove fresh bank consent.
- Live provider discovery chooses bank and country only inside a separately approved owner workflow. No hardcoded Revolut country/account, and owner completes linking/SCA.

## Verification boundaries

Protocol unit tests establish only the cases they exercise, including state, replay, expiry, cancellation and callback validation. Receiver tests use synthetic loopback traffic; admin HTTP tests use mock transport. Synthetic integration tests do not prove browser TLS, Windows certificate behavior, Windows protected storage, provider acceptance, mobile handoff, real bank consent or live data.

All those missing checks remain release gates. A local demo is not a live bank integration, and compiling prototypes does not authorize their use with real accounts.

## OAuth URL exception

The provider authorization redirect necessarily carries transient state and code parameters in the browser callback URL. This is the sole protocol-required exception to the ban on placing these values in URLs. Do not copy, retain, publish, log or reuse that callback URL. The relay must consume it privately and return only a constant page, never links carrying those parameters. Review browser-history and local observation exposure in the real Windows flow.
