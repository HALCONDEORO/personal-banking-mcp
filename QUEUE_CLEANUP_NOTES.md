# Queue cancellation boundary

Base: 3b830a0c41c557b863f3ad7f7e0f0377de5e5df6.

Synthetic local operations only. No provider connections, credentials or activation.

## Reproduction

When SerialQueue cancels a running operation whose cleanup raises, CPython 3.10.12 preserves caller CancelledError but emits an unretrieved raw operation exception through the loop handler. A synthetic cleanup canary is visible in that diagnostic. CPython 3.12.16 instead substitutes LoadStopped and the task is not cancelled. Both make one operation call, leave pending at zero and allow the next operation. This is a queue boundary defect, separate from the HTTP transports already corrected in PR34.

## Change

Extract the existing PR34 cancellation helper into a standard-library-only module and reuse it for the queue's running operation. The HTTP client keeps the same private alias, and admin still imports that alias. Use ensure_future instead of create_task because the queue accepts any awaitable, including an existing Future or a custom __await__ object. Lock acquisition and spacing are unchanged.

Six added queue tests cover cancellation/timeout with cleanup failure, cancellation/timeout whose operation suppresses cancellation and returns success, an existing Future, and a custom awaitable. They check one call, slot consumption, pending/lock cleanup, next operation and absence of unretrieved loop diagnostics where applicable.

Full composed suite:398 normal and optimized on CPython3.10.12 and3.12.16. Existing eight HTTP cancellation tests still pass. Node9/55/58 with seed398 and Python3.12 server. No independent review is implied by these author-run results.

Cleanup is cooperative, not a hard wall-clock bound. Repeated cancellation and work that refuses to terminate do not become process containment or a guarantee that arbitrary injected work has stopped. No concurrency guarantee is expanded beyond the reviewed queue contract. Merge requires independent exact-byte review and current CI.
