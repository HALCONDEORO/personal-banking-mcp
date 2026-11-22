# Local bridge contracts and missing implementation

Design and synthetic test scope only. Updated 22 November 2026 after the isolated
TLS, process-control, data and duplex-ACK proofs. No complete Windows banking
bridge is activated by this document. No executable owner certificate/key setup
is supplied. The fixture MCP does not start consent, sign tokens or read a bank.
See [the implementation map](docs/INTEGRATION_STATE.md) for current code paths,
exact proof boundaries and the next integration gates.

## Two different boundaries

Do not call both boundaries a single working bridge:

1. **Callback local hop:** the isolated Windows TLS relay rebuilds a narrowly framed
   plaintext request for the same laptop's loopback admin receiver. Python
   `callback_framing.py`, `callback_receiver.py` and `admin_consent.py` provide
   separately testable parsing, lifecycle and state checks. The .NET relay and
   hosted-runner TLS tests exist separately; the loopback hop still does not
   authenticate another local process. Synthetic private pipe proofs do not
   replace that runtime hop or supply a production host.
2. **Signing-to-transport boundary:** a proposed Windows-native signer creates a
   fixed provider JWT for a trusted in-process transport. The current Python
   read transport accepts a callable returning a token string. That callable is
   a seam, not an implemented or authenticated connection to a Windows signer.
   There is no supported CLI, IPC schema, socket, stdout protocol or general
   signing service in the repository. Do not invent one by passing tokens
   through process arguments, logs, clipboard or a public/local HTTP endpoint.

The selected topology remains Windows-local without SSH, tunnels, a server,
a public callback or a cloud relay. Loopback and a fixed Host header do not
supply local-process authentication. A listener binding is not an ACL.

## Callback-hop contract exercised by Python

- `relay_request` builds only the fixed GET/Host/Connection framing for a
  candidate callback target. `parse_relay_request` reconstructs the fixed
  private origin. Neither is a browser HTTP parser or a TLS implementation.
- Syntactically valid HTTP is not valid consent. State, one-use, TTL, code/error
  conflict and exact query/origin rules belong to `ConsentAttempt`.
- A locally accepted callback does not mean a provider session exists. The
  constant response explicitly says the bank session is not confirmed.
- Private callback code/state go only to the separate reviewed admin workflow.
  No MCP tool consumes them. No private URL should be logged or displayed.
- Tests must exercise the join, including a positive callback and replay, not
  merely assert that every malformed input is rejected.

A percent-encoded query can pass the framing layer and still fail consent
validation. That is expected layering, not permission for the relay to decode,
normalize, rewrite or forward browser headers. The .NET relay parses
its own TLS/browser input separately and rebuilds only the fixed local hop.

The current receiver requires EOF after the rebuilt request: the relay must
half-close its sending side. A blank line alone does not complete the input.
Its bounded read defaults to two seconds. Request maximum is 12,288 bytes;
framing target maximum is 8192 characters, but consent validation caps the
complete reconstructed URL at 8192, so the effective target limit is smaller.
A valid state with denial or invalid code consumes the attempt; unrelated
wrong-state traffic does not. The current receiver stops on success, terminal
failure, expiry or its eight-connection budget. These are prototype behavior,
not a Windows relay compatibility claim.

The existing POSIX private store refuses native Windows. Do not replace its
permissions checks with an ordinary file or present it as Windows storage.

## Signer seam: requirements, not guarantees

A future integration must fix and review all of these before real use:

- A single trusted owner-approved application/certificate binding, selected
  from private local configuration rather than MCP/user tool arguments.
- Only the fixed issuer/audience/algorithm/key ID and short token lifetime.
  No arbitrary claims, arbitrary data signing, caller-selected destination or
  credential export surface.
- Protected Windows key selection, exact certificate identity, key policy,
  certificate validity, disposal, rollback/time handling, concurrency policy,
  replacement and exact cleanup verified on the supported target system.
- In-process delivery only to a reviewed allowlisted transport. If the chosen
  runtime cannot support that, stop and review a new architecture. An opaque
  Python callable is not proof of Windows key custody or local authentication.
- Generic failure, no token in repr/errors/output, no automatic retry of a
  consent-changing operation, and explicit handling of uncertain remote state
  after timeouts/cancellation. A successful token format test is not signature
  verification, provider acceptance or authority to make a request.

The Windows stage1 owner receipt is a prerequisite for further Windows work,
not an approval for these missing stages. A build or synthetic primitive test
cannot establish persistent key ACLs, secure storage, a working signing bridge,
provider redirect support, bank linking or real-read authority.

## What the synthetic suites can and cannot show

`test_callback_contract_join.py` exercises actual Python framing plus actual
consent-state validation using in-memory synthetic targets. It makes no socket,
TLS, Windows, signer or provider call. Existing receiver tests use local
synthetic loopback sockets and existing admin transport tests use MockTransport.
The HTTP/read stack tests use the actual Python layers and injected mock HTTP.
Those Python suites do not compile or execute C#, create a key, prove target-OS
behavior, test real bank compatibility or change setup/activation gates. Separate
.NET TLS and process fixtures now supply hosted-runner evidence, as recorded in
the implementation map; they are not owner-laptop or real-bank evidence.

See [the selected callback design](LOCAL_CALLBACK_DESIGN.md),
[Windows release gates](WINDOWS_CALLBACK_DESIGN.md), and
[personal setup readiness](PERSONAL_SETUP_READINESS.md). Provider protocol
reference: https://enablebanking.com/docs/api/reference/ . Protocol documentation
is not approval of this local design or of any particular bank account.

## Fixed signer adapter (synthetic scope)

`signer_seam.py` provides `FixedSigner`, a fixed in-process adapter between a
reviewed zero-argument backend and `ReadOnlyHTTP(token=...)`. It checks that the
returned string has only the fixed header (RS256, kid equal to the application id)
and the four fixed claims (issuer, audience, iat, exp, lifetime at most 300 seconds,
not expired). It allows one call at a time, no retry, no cache, a single generic
error with no chained backend error, and no token in repr or pickle. It has no CLI,
listener, stdout or file surface and cannot be used as a general signing service.

It is a shape check only. It does not verify the signature, prove Windows key custody,
authenticate the backend, or show that the provider accepts the token. No Windows
backend exists yet. `test_signer_seam.py` uses only synthetic keys and
`httpx.MockTransport`.

## Static signer review, separate from the repository runtime

The separately supplied WindowsApiToken.cs candidate and stage1 Program.cs
were read without compilation or execution for this review. They do not call
the callback receiver or implement a TLS relay. The signer exposes an internal
.NET CreateToken method, not Python FFI, hosting or a transport bridge. Program
is an isolated self-test, not that missing adapter or a request coordinator.

The API signing certificate and the future TLS localhost certificate have
different roles. The proposed API signer checks RSA4096, CNG persistent signing
key policy, non-CA certificate and exact identity. The proposed TLS listener
requires localhost SAN/serverAuth, reviewed trust and exact cleanup. Do not
reuse one merely because both are called certificates. The self-test's
throwaway RSA2048 primitive is neither of those persistent certificates.
Stage1 does not call CreateToken and is not proof of actual API-token signing.

A future attempt coordinator is still missing. It must bind redirect/state/TTL,
selected bank/country, requested consent expiry, returned private session,
protected Windows storage and the GET account allowlist. A callback code is not
a signing input; a JWT is not callback state or proof of bank consent. The
signer's proposed 60-second JWT and the Python callback's 300-second TTL have
different purposes and need not match. No live-secret value belongs in a
receipt or screenshot. These notes do not implement any of the missing stages.
