# Contributing

Contributions should help someone reproduce the synthetic demo without credentials. Use English for code, pull requests and technical documentation; Spanish user-facing documentation is welcome alongside it.

## Workflow

1. Start from a current branch and create a focused topic branch.
2. Install the pinned dependencies in a virtual environment. Follow docs/TESTING.md.
3. Include tests that fail before the fix and pass afterwards. Use invented data only.
4. Open a pull request explaining the change, exact test commands, results and remaining limits.
5. Obtain independent review and green checks at the exact commit to be merged. Re-run checks after changing the head. Do not equate a local pass with remote CI.

Do not merge or deploy to bypass review. Publishing a release, changing repository visibility and adding provider access are separate maintainer decisions, not consequences of a test pass.

## Keep the boundary

- No payment, transfer, trading, card-change or account-changing tools.
- No generic HTTP, arbitrary URL, file-reader or shell tools exposed to the MCP client.
- No real statements, account numbers, customer identities, credentials, keys or session tokens in code, tests, issues, logs or screenshots.
- Do not add live-provider tests, authentication flows, external accounts or spending to CI.
- Keep provider experiments disconnected from MCP until their own design and implementation are reviewed. Synthetic transport tests are not evidence of live provider compatibility.
- Treat provider fields and transaction descriptions as untrusted data. Never execute them or treat them as approval.

## Dependencies and licensing

Explain why a dependency is needed, pin it through the appropriate requirements or lockfile, review its license and advisories, update inventories/notices, and preserve required copyright and license texts. A package metadata label alone is not a complete redistribution review. Do not copy external code without tracing its provenance and retaining its obligations.

## Good changes

Small reproducible fixes, strict validation, privacy-preserving error handling, clearer installation steps, deterministic negative tests and documented limitations are useful. Avoid claims of production readiness, whole-history completeness or real-bank support that the code and evidence cannot establish.

Report sensitive security issues as SECURITY.md describes, not with a public payload.
