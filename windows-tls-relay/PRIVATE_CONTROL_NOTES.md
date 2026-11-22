# Private child-control prototype, synthetic only

This change is a first process-control piece, not a complete Windows relay launcher. The Python SyntheticControlRunner starts exactly the bundled ControlFixture.dll using an explicitly configured absolute .NET runtime path. It does not choose a certificate, open a store, sign, start the TLS relay, call a bank or connect to MCP. The fixture is a real .NET subprocess, not a mock of process APIs. It has only fixed synthetic modes.

## Control and failure contract

- No shell. Fixed assembly path and an allowlisted synthetic mode argument. No code, state, token, callback URL or key is accepted. No bank credentials are needed.
- Inherited anonymous stdin/stdout pipes carry only exact bounded ASCII START 1, READY 1, DONE 1 and STOP 1 frames. Child stderr goes to DEVNULL. The parent prints neither channel, and public exceptions contain only a fixed category.
- The child receives a small environment allowlist, excluding bank-token variables, loader hooks and general inherited application settings. Runtime, assembly and their parent directory must already be trusted local configuration; there is no publisher/hash verification, immutable install or same-user attacker defense here.
- Unexpected/oversized output, trailing bytes after DONE, early exit, nonzero exit, elapsed monotonic deadline and repeated invocation fail. One runner instance owns one attempt. No automatic retry.
- Startup is shielded so cancellation cannot lose an acquired child. Cancellation during startup waits for the launch result and then reaps it. The total deadline is checked after startup too, but cannot put a hard bound on OS process creation.
- On every acquired-child exit path: best-effort STOP and stdin close, wait, terminate/wait, then kill/wait as needed. An API failure or unknown returncode is failure, never proof of cleanup. Repeated caller cancellation cannot interrupt the separately owned cleanup task. Cancellation is propagated only after cleanup returns.
- Cleanup may exceed the attempt timeout. Waiting after kill is deliberately not presented as a kernel-level deadline. Only the direct child is covered. No process-tree/job-object containment, power-loss guarantee or promise against hostile descendants inheriting pipe handles.

The zero-argument async callable shape can be supplied to run_local_attempt. A test confirms that existing supervisor closes its receiver when this synthetic child fails. That receiver is a lifecycle fake for this composition test, not a claim that a production .NET relay and real callback listener have been joined.

## Evidence

The focused runner requires at least 17 tests, exit zero and no skips, in normal and optimized Python. Tests launch real synthetic .NET children for success, early exit, trailing output, flood, timeout, uncooperative STOP, repeated cancellation, cancellation while the spawn result is pending, malformed input, EOF and no parent output. Additional injected process-API failures verify escalation through kill/wait and refusal on unverified cleanup. Environment and one-use checks are included.

The TLS workflow builds the fixture in Release and runs both Python modes on its hosted Windows runner. Its existing A/B and 75-assertion Debug/Release gates, pins and permissions remain unchanged. Local Linux execution is not native Windows evidence. No native Windows pass is claimed until the exact-head workflow is read after review.

## Still open

There is no production host selecting an approved certificate, no actual relay launched by this module, and no complete owner setup. A later change must independently integrate those pieces. The callback data hop remains the existing unauthenticated fixed HTTP loopback path, separate from these control pipes. No authenticated private data channel, Windows Job Object, target-laptop ACL/trust qualification, provider Production redirect, registration, consent or live-bank read follows. No activation instructions are supplied.
