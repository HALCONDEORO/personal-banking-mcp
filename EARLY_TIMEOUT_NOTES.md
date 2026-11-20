# Early timeout dispatch

A native Windows synthetic CI run exposed two failures where an asyncio timeout
could fire before `loop.time()` reached the nominal deadline. An injected probe
or transport that suppressed cancellation could then appear reachable, or the
session workflow could start an account read after timeout was requested.

The doctor now uses the existing owned-await boundary. The checked session uses
that boundary around each transport stage, as well as the outer workflow. A
cancelled session stage cannot swallow the workflow cancellation and proceed to
an account read. Existing clock checks remain in place for slow ordinary results.
No provider, signer, credentials or live data are involved.

`test_early_timeout.py` deterministically models early dispatch by widening the
event loop's private clock-resolution window and keeping a synthetic ready task.
Both regressions fail on previous main on Linux Python 3.12.16 and pass after the
fix. This is a controlled scheduling model, not a guarantee for every event loop
or proof of Windows success. Full local normal and optimized suites: 410 methods
OK each, no skips. Actual Windows rerun is separate evidence from its CI receipt.

Cancellation remains cooperative. A transport that refuses to finish cleanup or
blocks the event loop is not forcibly terminated. There is no hard wall-clock
shutdown, memory-erasure or continuous-consent guarantee. No automatic retry,
new tool or live activation is introduced. Rollback reverts these call sites and
the synthetic regression module together.
