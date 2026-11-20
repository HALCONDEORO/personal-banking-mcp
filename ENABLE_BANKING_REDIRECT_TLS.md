# Enable Banking redirect evidence and local TLS prototype

Checked 20 November 2026. This is a synthetic prototype, not a bank connection,
Windows qualification, provider approval or permission to install certificates.
No live mode, command-line relay launcher, provider API call, payment operation,
certificate creation, trust-store write or secret export is supplied.

## What the sources establish

| Source | Established claim | Not established |
| --- | --- | --- |
| [Enable Banking Control Panel](https://enablebanking.com/docs/api/control-panel) | Application registration has a redirect allowlist. Production on Enable Banking infrastructure additionally needs description, data-protection email, privacy and terms URLs. Restricted activation permits data retrieval only for linked accounts. | Acceptance of `https://localhost:8765/callback`, local certificates, particular ports or browser/platform behavior. |
| [Enable Banking API reference](https://enablebanking.com/docs/api/reference) | The browser returns to the supplied callback. Successful authorization supplies a code for `POST /sessions`; state is returned in the redirect query. | A generic URI example is not an environment-specific localhost or certificate policy. |
| [Enable Banking Quick Start](https://enablebanking.com/docs/api/quick-start/) | Register an allowed callback and pass it in the account-information authorization request. Its example uses HTTPS. | An HTTPS example alone does not confirm that a locally trusted self-signed leaf is accepted in Production. |
| [Securo integration documentation](https://docs.usesecuro.com/docs/features/bank-sync/enable-banking) | This third-party integrator reports exact callback matching and HTTPS in Production. | This is not an Enable Banking guarantee or approval of our loopback topology. |
| [ebcli documentation](https://pkg.go.dev/github.com/nicolasacchi/ebcli) | This third-party client documents local HTTP for local use but says Production requires public HTTPS. | It does not settle whether our exact HTTPS localhost URI is allowed. Public relay deployment is not selected or authorized here. |
| [Microsoft SslStream API](https://learn.microsoft.com/en-us/dotnet/api/system.net.security.sslstream.authenticateasserverasync) | .NET offers server TLS with authentication options and cancellation. | It does not qualify this relay or a Windows browser. |
| [Microsoft X509Store API](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.x509certificates.x509store) | .NET supports named certificate stores and explicit open flags. | Store presence does not prove browser trust, key custody or a private network boundary. |
| [RFC 8252](https://www.rfc-editor.org/rfc/rfc8252) | Native-app loopback redirects have a standards context, including loopback HTTP cases. | This does not override a provider's redirect registration policy. |
| [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112) | HTTP/1.1 message framing and request syntax matter at a relay boundary. | This narrow listener is not a general HTTP server or proxy. |

**Provider acceptance remains UNCONFIRMED.** The official pages reviewed do not
settle the exact localhost/port/certificate question. Third-party statements
about Production HTTPS are supporting reports, not an official answer. No
support request, app modification or provider registration was performed.

## Implemented boundary

`windows-tls-relay/Relay` is a .NET 10 library. It does not start on import, and
nothing connects it to the MCP tools or a real setup command. The public factory
opens only Windows `CurrentUser/My`, read-only, using an exact 40-hex certificate
thumbprint. It refuses non-Windows, missing/ambiguous matches, a non-RSA-CNG key,
a machine key or an export-enabled key. It never exports a key or modifies a
store. The selected leaf must have a private key, current validity, validity
span at most 31 days, explicit non-CA constraints, digital-signature usage,
Server Authentication EKU and exactly one localhost DNS SAN with no IP SAN.
This code path has **not** been executed against Windows certificate storage.

The public listener/forward destination are fixed:

`TLS 127.0.0.1:8765` -> `HTTP 127.0.0.1:8766`

Only the existing `/callback` contract is forwarded, with fixed backend Host and
Connection headers. All browser headers, including cookies, are discarded.
Host must be exactly `localhost:8765`; wrong methods, paths, absolute-form URLs,
fragments, malformed percent/UTF-8, duplicate fields, unknown query fields,
code/error conflicts, framing headers, forwarded headers and upgrade requests
are refused. It validates shape only. The existing Python `ConsentAttempt`
still owns constant-time state matching, expiry and one-use semantics.

TLS permits 1.2/1.3 and advertises HTTP/1.1 only. Header input is bounded to
12,288 bytes. Handshake, header read, backend connect/read/write and browser
response each have a two-second upper phase limit and are also bounded by the
five-minute total cancellation token. The backend hop sends a write half-close,
as required by `CallbackReceiver`. Backend bytes are never reflected: only an
exact match to the known success response yields the constant success page.
All other responses yield the constant rejection page. Both pages have no-store,
no-referrer and restrictive CSP headers, with no URL or provider text.

The accept listener closes after **one TCP connection**, even if that connection
is malformed or never completes TLS. Invalid first traffic therefore terminates
this relay, rather than supporting retry within the same relay. No keep-alive,
second request or retry is processed. Framing headers are rejected; any trailing
body/pipelined bytes are discarded on connection close. The network listener
does not wait for browser EOF to prove there are no trailing bytes. Do not claim
that every pipelined network callback is rejected before the first callback can
reach the backend. This is a one-request close-delimited boundary, not a general
request-smuggling defense for a reusable proxy.

Callers must close the independent Python receiver on **every** relay exit,
including first-connection TLS failure, cancellation or malformed callback. That
cross-process supervisor is not implemented here. No automatic retry is safe.

## Reproduce synthetic evidence

Prerequisites: .NET 10 SDK and Python 3 available as `python` on Windows or
`python3` elsewhere. No NuGet test packages, bank credentials, persistent
certificate, administrator privileges or trust-store changes are needed by the
harness. For SDK first-run hygiene, set `DOTNET_CLI_TELEMETRY_OPTOUT=1` and
`DOTNET_GENERATE_ASPNET_CERTIFICATE=false` before invoking dotnet. Do not run
`dotnet dev-certs https --trust` for this work.

```text
dotnet run --project windows-tls-relay/SyntheticTests --disable-build-servers
dotnet run --project windows-tls-relay/SyntheticTests -c Release --disable-build-servers
```

The harness generates temporary self-signed certificates in memory. Its TLS
client uses a custom in-memory trust store with normal hostname checks, not a
permissive certificate-validation callback. This is isolated test trust, not
browser trust. The Python join fixture starts the actual existing
`CallbackReceiver` and `ConsentAttempt` on a test-only ephemeral port. Synthetic
state travels through a private child-process pipe and is not printed in test
results. The test-only constructor allows ephemeral ports and shorter deadlines;
the public factory does not expose those substitutions.

Evidence for this change: Debug and Release each PASS 76 synthetic assertions on
Linux (.NET SDK 10.0.404), plus the existing Python 3.12.16 suite PASS 408 tests
both normally and with `-O`, and the existing MCP stdio demo PASS. An initial
full-suite run with the system Python 3.10 failed because MCP dependencies were
not installed; the complete successful runs used a fresh Python 3.12 environment
and the repository-pinned requirements. The TLS harness exercises actual TLS sockets,
fixed-hop rebuilding and EOF, Python receiver/state validation, hostname mismatch,
untrusted backend response, unavailable/slow backend, slow handshake/header,
cancellation/disposal, idle expiry, one-shot restart refusal and listener closure. Parser
and leaf-negative fixtures are additional coverage. These runs do not prove
Windows store custody or browser acceptance, and no Windows runner result is
claimed here.

## Gates that remain closed

1. Exact Production redirect URI, localhost/127.0.0.1, certificate and port policy
   must be confirmed by authoritative provider evidence. Do not infer acceptance
   from compilation, this harness or a third-party setup guide.
2. Independently review this implementation and the final commit. Then run the
   same harness on Windows and qualify CurrentUser/CNG custody with synthetic
   positive and refusal fixtures. No real key may be used as a test fixture.
3. Explain the exact leaf creation/trust/removal changes and get the owner's
   approval before doing any of them. No general development CA or certificate
   warning bypass. Certificate trust is not scoped cryptographically to a port.
4. Test the actual Windows browser with normal certificate checks and no warning,
   verify IPv4 resolution and that another LAN device cannot connect. IPv6 is
   not implemented. A browser choosing `::1` first can fail; never bind all
   interfaces as a workaround.
5. Review competing-local-process interception and fake-backend risks. Loopback
   and a fixed Host are not local-process authentication. The caller/supervisor
   and any private-channel improvement remain separate work.
6. Complete Windows protected storage and the admin bridge/supervisor. Review
   all listener cleanup paths across both processes. This library does not
   supply the complete linking workflow or store provider sessions.
7. Only then review the owner's intended registration settings and linking/SCA
   step. A phone's localhost points to the phone, not the Windows laptop.
   Browser history and local observation of callback URLs remain exposure risks.

Existing design documents remain design records. Where they say no TLS prototype
exists, this note adds the narrow library evidence above, not Windows readiness
or a live-flow claim. Nothing here authorizes money movement or credential use.
