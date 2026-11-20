# Testing

The repository's tests use invented data and local processes. No bank account, keys, account registration or live-provider access is needed. Some integration tests open ephemeral loopback TCP sockets and use temporary private files; HTTP provider tests use httpx.MockTransport rather than the network. Run commands from the repository root unless noted otherwise.

## Python suite and demo

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m unittest -v
python -O -m unittest -v
python test_server.py --demo
```

The full discovery commands above are verified on POSIX, not Windows: PrivateStore explicitly refuses non-POSIX systems and its tests and the synthetic admin integration are not automatically skipped there. Windows activation syntax in [the README](../README.md#quick-start) is not evidence that this whole suite passes on Windows. Do not weaken the store or delete failing tests to manufacture a green run. Run normal and optimized Python: validation must not depend on assertions that disappear under `-O`. A successful run on one OS is not evidence for another OS. The demo's stdout is JSON from actual MCP protocol calls using fixed synthetic fixtures. Protocol diagnostics may appear on stderr; do not add real data there.

The fixture MCP exposes exactly five tools: list_accounts, get_balance, get_transactions, search_transactions and summarize_transactions. Tests check the synthetic response envelope, decimal balances, currency separation, pending/booked states, dates, strict pagination types, unknown accounts/tools, copy isolation, fixture integrity and denied operations/origins/paths. Local stdio sessions cover normal startup, networking denied through a Python audit hook and startup from another working directory. The audit-hook scenario is not an OS sandbox or proof that every component has no network capability.

Unittest discovery also runs the isolated provider, analytics, callback, consent and storage tests. Passing those does not expose new MCP tools or activate a bank connection. Record the discovered method count and skips from your actual run rather than assuming a fixed total. Declarative vectors, fragments and subtests are not independent unittest methods.

## Node suite

Requires Node.js 22 or newer. The reviewed tree includes package.json, package-lock.json, tests and e2e:

```sh
npm ci --ignore-scripts
export SERVER_CMD="$PWD/.venv/bin/python"
export SERVER_ARGS="$PWD/server.py"
export FC_SEED=367
npm test
```

These exports are for a POSIX shell. In PowerShell, set `$env:SERVER_CMD`, `$env:SERVER_ARGS` and `$env:FC_SEED` instead, using the environment's Windows Python path. The harness requires an explicit target and must not silently select a mock. Its current argument parser separates on spaces, so use a checkout path without spaces for this suite. The Python server itself can use paths with spaces when its client passes proper argument arrays.

Property tests use a fixed seed for local reproduction; CI selects its own seed. Retain the failure output and actual seed. Fuzz cases check structured rejection and successful liveness probes. The e2e layer checks tool schemas, boundaries and playback-free stdio behavior. Canary tests patch a temporary copy of the synthetic server, require their anchor to exist and check that the synthetic description is returned as data without appearing in captured stderr. They do not prove that an AI client follows no external instructions or that every network channel is blocked. Synthetic adversarial strings in fixtures are test data, never setup instructions.

## Focused integration checks

Run the complete suites before merging. These shorter commands help investigate one layer; they do not replace full discovery or Node checks:

```sh
python -m unittest -v test_checked_read_http_integration test_checked_read_http_failures
python -O -m unittest -v test_checked_read_http_integration test_checked_read_http_failures
python -m unittest -v test_callback_contract_join test_callback_adversarial_corpus
python -O -m unittest -v test_callback_contract_join test_callback_adversarial_corpus
```

| Layer | What the tests exercise | What they do not establish |
| --- | --- | --- |
| Normalization and pagination | Injected responses, exact amounts, cursor handling, duplicate detection and page/row/byte/time budgets | Provider availability or complete bank history |
| Checked HTTP reads | Pager, session check and ReadOnlyHTTP together through MockTransport; valid row control, revocation, second-page failures, expiry and cancellation | Real sockets, TLS, network cleanup or atomic continuous consent |
| Callback contract and corpus | Actual Python framing/handler logic with synthetic readers/writers, prefixes, fragments and lifecycle states | Browser HTTP compatibility, backpressure, real half-close, TLS or Windows integration |
| Synthetic admin integration | Consent objects, mock HTTP, real ephemeral loopback TCP and temporary private POSIX storage | A supported Production redirect, Windows key custody or completed bank consent |

The pure pager's byte budget applies after the injected response is buffered. ReadOnlyHTTP separately tests streaming limits and redirect refusal with mock HTTP. Elapsed-time tests reject late results but cannot make a blocking event loop or cancellation-suppressing transport stop at a hard wall-clock deadline. Frozen wall-clock expiry tests model a boundary, not provider revocation latency.

Session authorization is checked before account reads, not atomically across a bank operation. A safe public exception or absent output canary is not evidence that private data has been erased from memory, traceback frames or every possible diagnostic channel. See [checked HTTP failure notes](../CHECKED_HTTP_FAILURE_NOTES.md), [callback corpus notes](../CALLBACK_ADVERSARIAL_NOTES.md), [local bridge contract](../LOCAL_BRIDGE_CONTRACT.md) and [synthetic admin integration notes](../ADMIN_INTEGRATION_TEST_NOTES.md) for their exact limits.

Keep Python corpus envelopes under tests/data. The Node fuzz corpus has its own array-only format; a Python manifest is not interchangeable with that input. Never enable live-bank calls in CI.

## Record evidence honestly

Record the exact commit, environment, commands, seed, skips and result. Distinguish your own local execution, a remote source read and another runner's CI receipt. Green CI applies only to its recorded head, not a later commit. After merging, verify the resulting main and repeat the relevant suites. Keep provider experiments disconnected from the real MCP until independently reviewed.

Use the project's installed Python environment for both unittest and SERVER_CMD. Missing mcp imports or an unset SERVER_CMD are setup failures, not passing tests or proof of a product defect. Preserve their output, correct the environment and rerun the unchanged candidate before reporting success.

Do not commit node_modules, virtual environments, credentials, real financial output or temporary canary copies. When changing dependencies, repeat the license/advisory review. A clean advisory scan is time-limited evidence, not a security audit. Synthetic tests do not establish provider availability, regulatory permission, multi-user safety or live financial correctness.

## JSON number boundary

`test_provider_json_numbers.py` covers shared strict decoding across the pager, checked session and separate admin response. It rejects nested exponent overflow as well as literal nonfinite values, with no retry, partial page result or account request after a refused session check. Finite extras and decimal-string money semantics are retained. All transports are synthetic. See [the finite-number notes](../PROVIDER_JSON_NUMBER_NOTES.md).


Session timezone offset and UTC-boundary regressions: `python -m unittest test_provider_session_offsets`. See `SESSION_OFFSET_NOTES.md` for scope and remaining limits.
