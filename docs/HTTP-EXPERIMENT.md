# HTTP/JWT transport experiment

This module is an experimental, opt-in library. It is not registered as an MCP tool or connected to the fixture-only server. Nothing in the default MCP enables live banking. No real bank or provider compatibility has been demonstrated.

Tests use httpx.MockTransport only. They need no account, bank consent, application registration or real key. Run both normal and optimized unittest discovery from the repository root.

The experiment signs a short-lived application JWT and constrains read requests to the nominated Enable Banking origin and account/session paths. Application setup and bank consent remain outside the module. There are no payments, POST tools, generic URL tools or automatic retries.

## Limits before any real use

- Diagnostic suppression attaches filters to logging handlers globally. This is an explicit process-wide policy, not isolated per-client protection. Handlers added or reconfigured later must be addressed again. It is not proof that all application logs are safe.
- Each adapter call now has a cooperative total deadline, default 5 seconds, including streaming reads. This is not a rate policy or a multi-call request budget; no total cross-call deadline is implemented. Blocking code or cancellation-suppressing cleanup still cannot be given a hard process-level time bound by this coroutine timeout.
- A cooperative coroutine deadline cannot provide a hard process-level bound when code blocks or suppresses cancellation.
- Consent, authorized account binding, private key storage, safe callback setup, retention and deletion require their own design and verification. This module does not implement a full connection flow.
- Unit tests with mocks establish regression behavior only. They do not establish live compatibility, bank availability, provider acceptance or production security.

Keep credentials and bank data outside the repository, CI, test evidence and public logs. Do not activate this experiment simply because its tests pass.
