# Read composition cancellation cleanup

The pager and checked-session wrapper now use the existing owned-await boundary,
matching the HTTP and serial-queue layers. A cancelled caller still receives
`CancelledError` when a synthetic transport raises during cleanup. The boundary
retrieves cleanup failures rather than leaving an unhandled task exception in
the event loop's default diagnostics. Timeout and cancellation-suppressing
success paths still fail closed.

`test_read_composition_cleanup.py` exercises cancellation during a session check,
an account read and pagination, with synthetic cleanup errors, timeouts and
suppressed cancellation. It checks call counts, event-loop diagnostics and the
checked reader's lock reuse. No real financial data or provider calls are used.

The initial three cancellation regressions failed on the previous main on Python
3.10 because cleanup exceptions reached the event-loop exception handler. The
candidate passes on Python 3.12.16, including optimized validation. This is local
evidence, not a claim about remote CI until the PR checks finish.

This remains cooperative cancellation. A coroutine can block the event loop or
refuse to finish cleanup, so neither the shared boundary nor these tests promise
a hard wall-clock shutdown or erasure of traceback frames and memory. Nothing is
wired into live banking or added to the MCP tool list.

Rollback: revert the two composition call sites, imports and this regression
module together. That restores the old diagnostic behavior; it does not change
consent, provider configuration or stored data.
