# Total HTTP deadline corrective patch

Base observed main: see patch-base.json. Apply this minimal patch only if the source context still matches; do not overwrite newer reviewed changes with the included execution copies.

httpx.Timeout(5) controls separate I/O inactivity/operations, not total elapsed streaming time. The pager already imposed a total budget, but direct balance/session HTTP calls did not. This patch bounds each transport call with asyncio.wait_for and a monotonic deadline capped at five seconds. Callers can choose a lower positive total_seconds; bool/NaN/infinity/invalid ranges are rejected.

Deadline is rechecked after the synchronous JWT supplier, response headers, each delivered raw chunk, stream completion and the outer await. That prevents late successful results when a transport suppresses cancellation or the token supplier blocks temporarily. HTTP inactivity timeouts remain defense in depth. No automatic retry is added. A timeout yields only `time_budget`, no private provider data.

Cooperative cancellation limitation: Python cannot forcibly preempt a blocking synchronous token supplier, a malicious transport that never yields or indefinitely suppressed cancellation/cleanup. In-process checks prevent accepting a late result; they are not a hard process kill. The host supervisor needs its own process-level deadline if a guaranteed wall-clock stop is required. Existing requests are read-only GET, but an uncertain timeout must not be retried automatically or described as proof of no external request.

Four new regression tests: slow-drip streaming, successful return after cancellation suppression, slow blocking token supplier rejected before HTTP, and invalid timeout configuration. Twenty-two HTTP/JWT tests pass normal and optimized Python. All use httpx.MockTransport and ephemeral synthetic keys, not provider traffic. No new dependencies, external code copy, credentials, bank setup or host deployment. Existing source licenses remain unchanged.
