# HTTP cancellation and cleanup

Synthetic transports only. No credentials, network requests or bank activation.

## Reproduction

On the prior implementation, cancelling a read/admin request during streaming while stream cleanup raises has different symptoms:

- CPython 3.10.12: the caller receives CancelledError, but the internal task can report an unretrieved sanitized failure.
- CPython 3.12.16: the caller instead receives FetchStopped/AdminStopped and is not cancelled. The configured CI Python family is 3.12.

Both paths make one request, with no retry or partial success. These observations are bounded to the tested versions, not every Python release.

## Change

A shared private helper shields the separately owned request task from implicit wait_for cancellation. The helper explicitly cancels and drains it on caller cancellation or timeout, retrieves cleanup failures, and preserves the original cancellation/timeout. A result callback also retrieves a later task exception if repeated caller cancellation interrupts the drain. Existing post-deadline success rejection remains in place.

This remains cooperative cleanup, not an OS-enforced deadline. A transport that never finishes cleanup can still prevent a single cancellation or timeout drain from finishing. No process containment or provider-side cancellation is claimed.

## Evidence

Eight added tests cover both read and admin paths: cancellation plus failing cleanup, timeout plus failing cleanup, suppressed cancellation returning success, and repeated cancellation during cleanup. They check cancellation identity, one request, one close and no unhandled loop diagnostics. The read timeout keeps the time_budget code.

The eight tests against the prior implementation on CPython 3.12.16 give 3 failures and 2 errors. With this candidate they pass on CPython 3.10.12 and 3.12.16. Full suite: 392 tests in normal and optimized modes on each interpreter. Node suites: 9/55/58 with seed 392 and the Python 3.12 server. Dependency compatibility and diff checks pass.

Base: a4e1f9d5787bb52064d766feddb6da218137d040. Merge requires independent exact-head review and current CI 3/3.
