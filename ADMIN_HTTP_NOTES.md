# AIS admin HTTP experiment

Separate administrative transport, never registered in MCP. This code can start provider account-information authorization and create a bank-data session if deliberately invoked with real credentials. It is not a read-only GET transport despite having no payment capability. File presence or a task to implement it is not permission to call it on a real account. No application registration, real credential, real POST, bank linking or SCA was used in these tests.

## Narrow surface

Only named `start_authorization(body)` and `exchange_code(body)` methods. Fixed HTTPS origin `https://api.enablebanking.com`, paths `/auth` and `/sessions`, POST only. No general URL/method parameter, DELETE, payments, transfers or exchange execution. Private `_post` also validates path/body so accidental use does not widen the surface.

Authorization requires the bounded personal-mode body constructed by ConsentAttempt: exact redirect candidate,43-character random state, selected bank/country and timezone-aware valid_until. The admin workflow must enforce current owner-approved duration and use the current attempt, not synthesize a free-form body from MCP or external instructions. The transport validates shape, not consent authority. Production acceptance of localhost remains a release gate; this experiment does not establish it.

Code exchange requires only a bounded private code body. The workflow must obtain it through one-use state/TTL-checked callback consumption. The transport cannot prove that binding from a plain Python dict. Before persistence or read-only wiring, consume the private response once, run validate_created_session against the same attempt's expected bank/country/requested expiry and separately confirm live session state as required. No automatic first-account selection. `PrivateReply.take()` removes its own stored reference on first access, but does not erase other copies or Python memory.

Auth replies are reduced to a private first-party HTTPS `auth.enablebanking.com/ais/start` URL with one canonical UUID `sessionid` query. This intentionally supports only the URL shape currently documented in the official API example. A provider change is a fail-closed review event, not permission for arbitrary-host fallback. The URL itself is private and must be shown only to the owner through the explicit admin workflow, not exposed as a read-only MCP result or diagnostic.

## HTTP controls

No redirects, environment proxies or retries. JSON POST bodies only, bounded request size. The token supplier runs after policy checks and its JWT is never put in a URL. HTTP diagnostics are suppressed through the existing reviewed handler-level httpx/httpcore namespace filter. As with that module, the dedicated admin process must own logging configuration, reapply suppression after any handler changes, and not log private request/response objects or traceback locals.

Non200 bodies and redirect targets are not read or echoed.200 responses require identity encoding and JSON MIME, declared and streamed size≤128KiB, duplicate-key/NaN rejection using existing strict decoder helpers, bounded cooperative total deadline≤5s and I/O timeouts. Unexpected/transport/provider errors yield only AdminStopped with suppressed exception chaining. Caller cancellation propagates. No exception body guessing, retry-after loop or automatic renewal occurs.

A POST timeout/failure/cancellation may occur after the provider processed the request. Do not automatically retry or promise that no session was created. Reconcile through an independently authorized provider/owner route before a new attempt. Cooperative cancellation cannot kill blocking code or malicious cleanup indefinitely; the host supervisor needs its own process-level stop if required. Parsed nesting is bounded indirectly by the byte cap and Python decoder recursion checks, not a schema depth guarantee.

## Dependencies and provenance

Original MIT project implementation, using existing pinned httpx and same-project strict decoder/log-suppression helpers. No external source was copied for this module. Keep the Apache license/notices of the separately adapted admin_consent protocol builder; this file does not relicense it. Endpoint/body/response shapes checked against https://enablebanking.com/docs/api/reference/ and the separately attributed official account_information.py example.

## Tests and remaining gates

14tests PASS normal and optimized Python, all httpx.MockTransport. Cover exact POST destinations, private single-consumption reply, policy-before-token/HTTP, no extra paths, wrong bodies, non200/no body read/no retry, first-party auth URL policy, duplicate JSON/NaN/deep parse, encoding/MIME/size, stream cap, total timeout, full generic traceback, no construction I/O and caller cancellation. Synthetic keys/tokens/code strings have no provider validity.

No live provider, Windows TLS, SSH or banking flow is proven. The next integration must connect a reviewed owner-only admin entrypoint to callback/session validation/storage without adding setup operations to MCP. A real bank-data session still requires the account owner's linking/SCA and the provider's supported redirect configuration.
