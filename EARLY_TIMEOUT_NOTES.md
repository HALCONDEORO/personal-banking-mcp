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
## Controlled deadline scheduling in the checked-session test

A later Windows portable run at head a2a59189 failed an older test's assertion
that exactly one transport had started within a 10ms wall-clock timeout. It
observed zero calls, a safe refusal before the first effect. That test had not
actually established the cancellation-suppression precondition on that run.
The failing receipt remains a failure, not evidence to discard through a rerun.

The replacement test signals actual entry into the first synthetic session
transport before expiring a logical monotonic deadline. Only
provider_checked_session's asyncio reference is replaced by a narrow clock
facade; the actual event loop clock and real async_boundary implementation are
unchanged. A scheduling wrapper retains the real owned outer task, waits for
transport entry, advances the controlled clock past its deadline, then invokes
the real owned-await zero-timeout path on that already-started task. The fake
transport explicitly records that it suppressed cancellation and returned a
response. The test requires that signal, exactly one session-check call, no
account read, the expected two ownership boundaries and a released lock. Its
separate 2s/5s real-time watchdogs detect a stuck test, not the behavior under
assertion. An acquired test transport task is cancelled/joined in finally too.

A second controlled case expires the logical deadline before the workflow starts
and requires zero transport entries, one outer boundary and a released lock.
These are distinct cases: accepting zero calls in the first case would weaken
coverage, so its exact-one-call assertion is retained. There is no larger
production timeout, retry, runtime fix, provider access or relaxed Windows gate.
Native Windows normal/optimized receipts are still required independently.
