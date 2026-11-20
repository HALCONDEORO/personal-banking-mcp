# Windows synthetic CI scope

`windows-synthetic.yml` adds a native GitHub-hosted Windows runner for the
existing portable Python surface and the synthetic MCP stdio demo. It installs
the same pinned requirements as Linux and uses the same pinned checkout and
Python setup actions, with read-only repository permissions and no secrets.

Both PR and main-push triggers filter to Python source/tests, requirements.txt
and this workflow. Documentation-only edits do not launch this Windows job.
Concurrency is grouped by workflow/ref with cancel-in-progress, so a superseded
run on the same PR or main is cancelled. Distinct PRs can still run concurrently;
this is not a global spending cap. Do not request manual reruns in bulk or raise
the owner's existing Actions budget. This public repository uses the standard
windows-latest runner, not a larger paid runner; recheck billing policy and
visibility if either changes. GitHub's current runner reference documents free
standard hosted-runner use for public repositories:
https://docs.github.com/en/actions/reference/runners/github-hosted-runners


`run_portable_tests.py` lists its modules explicitly. It runs both normally and
with `-O`; import failures, failures, an empty suite or any skipped test make the
step fail. New test modules do not silently join this Windows gate. Review and
add them deliberately. Full discovery on Linux remains unchanged and mandatory.

The selected set contains 378 test methods at the initial candidate. It includes
five-tool fixture protocol tests, no-network fixture checks, provider HTTP mocks,
session checks, bounded pagination, cancellation cleanup, analytics, exports and
synthetic loopback callback tests. It excludes the POSIX private-store modules
and the POSIX-store admin integration, which continue to run in full Linux CI.
This is an explicit subset, not a skip-based claim that full discovery works on
Windows.

Local pre-publication evidence: Python 3.12.16 on Linux, normal and optimized,
378 methods OK in each run, no skips. The Windows workflow is the source for the
actual Windows result after publication. Do not label the local run Windows.

A first Windows run deliberately failed rather than skipping defects. It exposed
early timer cancellation issues fixed separately in PR40, plus the networking
audit test's startup order. The revised no-network launcher constructs event-loop
infrastructure before installing its audit hook, then imports and runs the real
server entry point under the hook. Windows may require local sockets to construct
its event loop. No destination is exempted after the hook starts. A regression
checks that fixture code cannot resolve, connect or bind. This is not an OS
sandbox and does not claim the pre-hook infrastructure made no local socket call.

The runner includes the PR40 early-dispatch regressions. After that dependency
and the launcher change, local Linux normal/optimized runs select 381 methods,
zero skips. Only a green Windows run at the final PR head supplies Windows
execution evidence; prior failing runs and local Linux passes do not.

A green Windows run establishes only the exercised behavior on that hosted
runner. It does not test the owner's laptop, Windows key storage, a signing
bridge, persistent ACLs, TLS certificate trust, provider redirect acceptance,
real consent or a bank read. It does not enable a live mode. No real account,
private certificate, key, JWT, code or banking credential belongs in this CI.

Rollback: remove this workflow, explicit runner and note, and restore the old
inline audit test launcher. Product cancellation fixes belong to PR40 and are
not rolled back with this CI change. Existing Linux and Node workflow definitions
are untouched.
