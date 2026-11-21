# Synthetic TLS CI gate

The TLS synthetic harness workflow runs on a standard GitHub-hosted Windows
runner with Python 3.12 and .NET 10, in Debug and Release. This is a new native
runner check, not a claim about the owner's laptop or browser. It installs the
repository's Python requirements to exercise the existing private-pipe Python
receiver join. No production code changes are included. The reviewed KeyProbe source is synchronized exactly from main.

Each mode must exit successfully and print exactly one successful assertion
receipt with at least 75 assertions. The current harness has 76 assertions on
Linux but omits one non-Windows-store rejection on Windows, giving 75. An empty
run or missing receipt fails. The final assertion receipt ends with
`No bank/provider/trust-store changes.` Each Windows mode must also emit exactly
one `TLS-CLEANUP: all named keys absent` line BEFORE its final PASS, and exit zero.
The assertion threshold remains 75. The harness does not use a skip-capable test runner.

Before the existing harness, a separate CI-only KeyProbe runs in both modes.
It compares an ephemeral RSA fixture with a TEMPORARY PERSISTENT named CurrentUser
CNG key on the disposable GitHub runner. It verifies cleanup and uses no
certificate/trust-store installation. See KEY_AB_NOTES.md for the guards and
abrupt-termination limit. It is not authorized on the owner's laptop.
A/B success is distinct from the existing harness's assertion receipt.

The existing harness creates short-lived certificates in memory and uses custom
in-memory test trust. On Windows its normal TLS fixtures now use temporary PERSISTENT
named CurrentUser CNG signing-only, nonexportable keys, restricted to the disposable
GitHub runner by the same accidental-use guard. All owned tasks are joined and
certificate/relay scopes finish before key handles close and keys are deleted and
verified absent. Abrupt termination can bypass finally. See
WINDOWS_TLS_FIXTURE_NOTES.md. Socket fault-injection tests use only ephemeral RSA
and loopback sockets, including on Windows. The server-fault case deliberately
closes its peer without a TLS handshake; it does not require ephemeral-key TLS
success and does not create named CNG keys. CI does not run dev-certs, install a trust root, call the
provider, use a bank key or change a bank account. First-run SDK certificate
creation is disabled. Native setup actions are commit-pinned, permissions are
read-only, checkout credentials are not persisted, and the job has a ten-minute
limit. Path filters and cancel-in-progress prevent unrelated or obsolete runs.

Native Windows results must be read from the final-head workflow before merge.
A successful runner still does not qualify Windows browser trust, CurrentUser
key custody, ACLs, a full process launcher, provider Production redirect support,
physical-device return, or real account linking. See ENABLE_BANKING_REDIRECT_TLS.md
for the separate implementation limits. No billing setting is changed.
