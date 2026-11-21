# CI-only Windows key A/B

Do not run this probe on the owner's laptop. The entrypoint requires Windows
and GITHUB_ACTIONS=true. This variable is an accidental-use guard, not proof of
isolation. Only the disposable standard GitHub Actions runner is authorized.

A uses the existing in-memory RSA certificate. B creates a synthetic named
CurrentUser CNG key which IS PERSISTENT while the probe runs. It is nonexportable,
not a machine key, and its self-signed certificate is not installed in any
certificate or trust store. No bank key or account is involved.

Finally attempts deletion by its exclusive randomly generated name even if
creation failed. Absence verification runs even when deletion throws. Failure
or unverifiable absence keeps the process red with fixed failed/unknown output.
An abrupt process termination can bypass finally, so this is only for a
disposable runner. Synthetic tests exercise delete/exists failures and creation
failure states. No exception details or identifiers are emitted.

The proposed workflow runs Debug and Release A/B before the existing TLS
harness, aborting on failure. A/B success is separate evidence and does not
make the unchanged harness pass. PR45 stays on hold until its own native
receipt and final-head review pass.
