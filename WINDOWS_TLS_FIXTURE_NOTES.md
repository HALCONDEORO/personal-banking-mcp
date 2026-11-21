# Windows synthetic TLS fixture key lifetime

This change is only for the synthetic test executable, not LocalTlsRelay or the owner's setup. On Windows the executable requires GITHUB_ACTIONS=true and is authorized only on a disposable GitHub Actions runner. The variable is an accidental-use guard, not proof of isolation. Do not run it on the owner's laptop.

The existing in-memory RSA fixture failed during server authentication on the Windows runner. The reviewed A/B diagnostic on head638c06d passed in Debug and Release with unchanged certificate validation: ephemeral fixture rejected, named CurrentUser CNG fixture handshook successfully, and the named key was deleted and verified absent. The job remained red because the original harness still used the ephemeral fixture.

The Windows fixture factory now creates random exclusive named CurrentUser CNG keys, nonexportable and signing-only. These keys ARE PERSISTENT for the life of the synthetic harness. The self-signed certificates remain in memory and are not installed in any certificate/trust store. Linux keeps the existing ephemeral RSA factory. No hostname or certificate-validation checks are relaxed.

Each owned name is tracked before key creation, including partial creation failures. The original CngKey handles remain owned until all test methods have exited, avoiding reliance on temporary key-handle disposal behavior. At the outer harness finally, handles are closed and deletion is attempted for every tracked name, followed by absence checks even if deletion throws. A failure or unverifiable absence keeps the process red. Network, rejection and Python-join fixture scopes cancel/unblock and await their own tasks in finally before certificate disposal. The independent server probe awaits both tasks with WhenAll. The deliberate dispose rejection variant still calls relay.Dispose while its run unwinds, as before, but awaits that run before returning or final key deletion.

Cleanup-policy tests inject deletion failures, existence-check failures, surviving keys, and pre/post partial creation failures through the same tracking helper. Separate asynchronous model tests cover early client failure, cancellation, server failure and cleanup failure, asserting zero active tasks and fixture-scope exit before Delete. These are policy models, not evidence that native Windows fault paths have run. The final PASS line is emitted only after successful final cleanup. No names, certificate fields or exception details are printed.

Both ownership lists and fixture allocation are intentionally single-threaded. Do not parallelize test methods or fixture allocation without synchronizing ownership and shutdown. Internal network workers do not allocate certificates or add keys.

Network and rejection setup now lives inside the resource-owning try from backend.Start onwards, with nullable relay/tasks. Partial setup still stops the backend and joins every task that started. The independent server probe also covers partial Task.Run setup. Python child termination always waits in finally even if Kill fails.

Focused socket fault hooks run the actual NetworkTests resource path with ephemeral RSA and loopback only: setup failure after backend.Start, early client failure after both relay/backend work has started, server failure via peer close without TLS, and server cancellation. They assert joined tasks, closed backend/relay listeners, and scope exit. The optional --socket-faults-only argument runs only these cases, not named CNG fixtures; the Windows CI-only guard still applies. This isolated mode emits no assertion PASS receipt, so it cannot satisfy the workflow gate.

The matching workflow now requires exactly one all-named-keys-absent cleanup receipt before exactly one final PASS ending in No bank/provider/trust-store changes., at least 75 assertions, and exit zero. The threshold and exit-code gate are unchanged.

Abrupt process termination can bypass finally. This is not a general secret custody or guaranteed cleanup mechanism. Only a disposable runner is authorized. A successful assertion receipt alone is not enough: process exit zero and the final all-keys-absent receipt are required on Windows. No owner-laptop, browser-trust, ACL, Production redirect or real-bank claim follows.

The earlier ENABLE_BANKING_REDIRECT_TLS.md describes the original Linux evidence and in-memory fixtures. It does not describe this later Windows-specific persistent-key lifetime. This note qualifies that earlier fixture description for Windows synthetic runs only.
