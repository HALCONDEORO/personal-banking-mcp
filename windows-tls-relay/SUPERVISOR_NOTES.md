# Cooperative receiver lifecycle helper

This follow-up adds `relay_supervisor.py`, a Python coroutine join. It does not
start a Windows process, load a certificate, call a provider or add an MCP tool.
It is separate from the initial reviewed TLS prototype snapshot.

`run_local_attempt(receiver, run_relay)` starts the supplied receiver before
invoking the zero-argument async runner. It returns a private callback result only
when the receiver succeeds and the runner also completes. It attempts receiver closure
in `finally` before cancelling/joining runner and waiter tasks. The two cleanup
stages are independent: a close exception cannot skip task cancellation/join. All caller-visible
failures are generic except `CancelledError`, which retains cancellation meaning.
The receiver close and runner must be cooperative. The runner must keep all its
work in the supplied task and stop its relay on cancellation. Joining a cancellation-resistant task can still hang;
receiver closure was already attempted before that join, but is not guaranteed
when close failed. A close failure produces a generic error, never success or a
listener-closed claim. Repeated caller cancellation cannot interrupt the separate
shielded cleanup task. Cancellation is re-raised only after cooperative cleanup
finishes, and takes precedence over a close error. This helper is not process
containment, a kill deadline or a detached-child cleanup guarantee.

Seven socket-backed tests exercise success, provider denial, a runner failing
before any connection, clean runner exit without callback, cancellation, a
callback followed by a runner that does not exit, and receiver bind failure.
These seven tests assert that the consent attempt is closed, receiver listener is gone,
handler task set is empty and its known TCP port refuses new connections. The
runner-never-exits test verifies cooperative cancellation, not forced termination.

```text
python -m unittest discover -s windows-tls-relay -p test_relay_supervisor.py -v
python -O -m unittest discover -s windows-tls-relay -p test_relay_supervisor.py -v
```

Five additional fault-injected lifecycle tests cover close errors, original
cancellation plus close error, repeated cancellation during blocked close,
repeated cancellation plus close error, and first cancellation during cleanup.
They verify both owned tasks are joined even on close failure, while refusing to
claim listener closure in the failure case. These five use a lifecycle fake, not
a real socket or Windows runner.

Both modes pass 12/12 on Linux Python 3.12.16. The Linux fixture-check workflow
runs this suite explicitly with `run_supervisor_tests.py`, normally and with
`-O`. The runner fails on errors, failures, any skip or fewer than 12 executed
tests; root discovery alone does not include this subdirectory. This gate is
Linux lifecycle evidence, not Windows or .NET process qualification. These tests join the actual existing
Python receiver with a synthetic async runner, not a launched .NET executable.
The separate .NET TLS harness still supplies its actual TLS/Python callback join.
A Windows-specific process launcher, private channel and full owner setup remain
unimplemented. The helper alone does not close that full integration gate.

## Trailing-byte boundary

Rejecting every possible late body/pipelined byte before the first backend
forward is not guaranteed by a keep-open HTTP/1.1 browser callback. Waiting for
browser EOF before responding can deadlock normal browsers. A peek only sees
bytes already available and cannot rule out bytes that arrive after the peek.
The library rejects framing headers, processes one request, closes the listener
and discards anything trailing when closing the connection. It does not claim
an all-timing pre-forward trailing-byte rejection guarantee. A different browser
protocol or separately approved topology would be needed to change that bound.
