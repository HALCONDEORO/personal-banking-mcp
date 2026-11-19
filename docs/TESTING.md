# Testing

All tests use invented data and local processes. No bank account, keys, account registration or live-provider access is needed. Run commands from the repository root unless noted otherwise.

## Python baseline

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m unittest -v
python -O -m unittest -v
python test_server.py --demo
```

Windows activation is documented in README.en.md. Run normal and optimized Python: validation must not depend on assertions that disappear under `-O`. The demo's stdout is JSON from actual MCP protocol calls using fixed synthetic fixtures. Protocol diagnostics may appear on stderr; do not add real data there.

The baseline checks the exact three-tool surface, synthetic response envelope, decimal balances, currency separation, pending/booked states, dates, strict pagination types, unknown accounts/tools, copy isolation, fixture integrity, allowed read policy and denied operations/origins/paths. Local stdio sessions cover normal startup, networking denied through a Python audit hook and startup from another working directory. Additional tests in later PRs extend this list.

## Supplemental Node suite, when included

Requires Node.js 22 or newer. Only run this block when package.json, package-lock.json and the tests/e2e harness are present in the reviewed branch:

```sh
npm ci --ignore-scripts
export SERVER_CMD="$PWD/.venv/bin/python"
export SERVER_ARGS="$PWD/server.py"
export FC_SEED=367
npm test
```

These exports are for a POSIX shell. In PowerShell, set `$env:SERVER_CMD`, `$env:SERVER_ARGS` and `$env:FC_SEED` instead. The harness requires an explicit target and must not silently select a mock. Its current argument parser separates on spaces, so use a checkout path without spaces for this suite. The Python server itself can use paths with spaces when its client passes proper argument arrays.

Property tests use a fixed seed for reproduction; retain the failure output and seed. Fuzz cases check structured rejection and successful liveness probes. The e2e layer checks tool schemas, boundaries and playback-free stdio behavior. Canary tests patch a temporary copy of the synthetic server, require their anchor to exist and check that the synthetic description is returned as data without appearing in captured stderr. They do not prove that an AI client follows no external instructions or that every network channel is blocked.

## Provider experiments, when included

`provider_normalize.py` and `provider_pager.py` are independent pure/simulated modules, not a live provider adapter. Unittest discovery includes their tests when present. Use injected synthetic responses for empty pages with cursors, repeated tokens, duplicate references, bad JSON, malformed records, rate limits, expired-consent statuses and page/row/byte/time budgets. Never enable live-bank calls in CI. Tests must distinguish provider-pagination exhaustion from full-history availability.

Elapsed-time tests reject late results. They cannot make a blocking event loop or cancellation-suppressing transport stop at a hard wall-clock deadline. The simulated response-byte limit occurs after buffering; a future HTTP transport needs its own streaming limit and redirect refusal.

## Record evidence honestly

Record the exact commit, environment, commands and result. Distinguish your own local execution, a remote source read and another runner's CI receipt. Green CI applies only to its recorded head, not a later commit. Keep unrelated provider tests disconnected from the real MCP until independently reviewed.

Do not commit node_modules, virtual environments, credentials, real financial output or temporary canary copies. When changing dependencies, repeat the license/advisory review. A clean advisory scan is time-limited evidence, not a security audit. Synthetic tests do not establish provider availability, regulatory permission, multi-user safety or live financial correctness.
