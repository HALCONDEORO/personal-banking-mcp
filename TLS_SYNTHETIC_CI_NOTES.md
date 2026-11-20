# Synthetic TLS CI gate

The TLS synthetic harness workflow runs on a standard GitHub-hosted Windows
runner with Python 3.12 and .NET 10, in Debug and Release. This is a new native
runner check, not a claim about the owner's laptop or browser. It installs the
repository's Python requirements to exercise the existing private-pipe Python
receiver join. No production code or fixture changes are included in this PR.

Each mode must exit successfully and print exactly one successful assertion
receipt with at least 75 assertions. The current harness has 76 assertions on
Linux but omits one non-Windows-store rejection on Windows, giving 75. An empty
run or missing receipt fails. The harness does not use a skip-capable test runner.

The existing harness creates short-lived certificates in memory and uses custom
in-memory test trust. CI does not run dev-certs, install a trust root, call the
provider, use a bank key or change a bank account. First-run SDK certificate
creation is disabled. Native setup actions are commit-pinned, permissions are
read-only, checkout credentials are not persisted, and the job has a ten-minute
limit. Path filters and cancel-in-progress prevent unrelated or obsolete runs.

Native Windows results must be read from the final-head workflow before merge.
A successful runner still does not qualify Windows browser trust, CurrentUser
key custody, ACLs, a full process launcher, provider Production redirect support,
physical-device return, or real account linking. See ENABLE_BANKING_REDIRECT_TLS.md
for the separate implementation limits. No billing setting is changed.
