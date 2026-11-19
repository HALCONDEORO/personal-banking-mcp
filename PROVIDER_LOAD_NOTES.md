# Local serial queue and multi-call budget prototype

Internal scheduling primitive only, not wired to MCP, HTTP or an admin entrypoint. No constructor I/O, background task, retry, bank call, credential, disk write or rate-limit bypass. Existing per-request HTTP limits remain separate.

`CallBudget` gives one explicit workflow a finite monotonic lifetime (up to300seconds) and a finite call count (up to100). Reservation happens immediately before calling an operation; spent slots are not refunded on exception, timeout or cancellation. These are local maximum bounds, not recommended provider rates or approved API quotas. A caller choosing a new budget for every request defeats cross-call accounting; the workflow must own and share the same budget.

`SerialQueue` runs one awaitable operation at a time, caps active+waiting jobs (default8), and spaces operation starts (default2seconds). It must be instantiated and shared at the intended provider/account scope; it is not automatically global, cross-process or cross-account. No queue instance is created by module import. Reuse across event loops is rejected. Waiting for the lock, interval and operation consume the same supplied budget. Failed operations and cancelled running operations release the lock, waiting cancellation does not release another job's lock. A failed attempt still counts as an operation start for spacing.

Clocks and sleep are injectable for deterministic synthetic tests. Backward/nonfinite clocks and early-returning sleep refuse rather than shortening an interval. Operator controls and actual provider-specific rate policy must be decided separately from these mechanism defaults. No retry or automatic renewal occurs. Errors are generic with no provider/operation exception text; cancellation propagates. Generic errors do not erase private objects or Python memory. Callers must not print callback locals, results or exception object internals.

## Limits

Cooperative asyncio timeouts do not forcibly stop synchronous blocking code, a coroutine which suppresses cancellation or hostile cleanup. The operation factory must be trusted and nonblocking; it is not a sandbox. A hard process supervisor would be a separate design. Waiting and timeout can finish after the nominal deadline because cancellation is awaited; a timeout is not proof of remote rollback. Do not use this mechanism to retry an uncertain provider POST.

The primitive returns the operation's private result to its trusted caller; it does not make that result safe for an MCP response, log or screenshot. No callback, session or consent authority is created by a slot reservation.

## Provenance

Adapted the small serial queue/spacing/injected-clock pattern from `src/load-control.mjs` at HALCONDEORO/tesco-ie-grocery-mcp pin08db94c5230ab74d9a573415442e22a5961e5c69, MIT, Copyright(c)2026MarcoTevar. Preserve LICENSES/tesco-ie-grocery-mcp-MIT.txt and existing attribution. Changes: Python asyncio, bounded pending jobs/count/deadline, monotonic checks, cancellation and generic errors. No upstream challenge detection, arbitrary fetch or error-message interpolation was copied.

Source: https://github.com/HALCONDEORO/tesco-ie-grocery-mcp

## Local tests

19 synthetic tests pass normal and optimized Python with warnings as errors. Covers count/time validation, exhausted slots, expiry, backward clocks, serialization and spacing, pending cap, generic errors without retry, invalid result type, cancellation of active and waiting jobs, insufficient interval budget, early sleep and cooperative timeout. No provider quota, network, real Windows scheduling or cross-process behavior is proven.

Pinned adapted source: https://raw.githubusercontent.com/HALCONDEORO/tesco-ie-grocery-mcp/08db94c5230ab74d9a573415442e22a5961e5c69/src/load-control.mjs
