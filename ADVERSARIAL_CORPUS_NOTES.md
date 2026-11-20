# Declarative banking boundary regression corpus

The JSON in `fuzz-corpus/banking-session-reads.json` contains 77 synthetic cases
created against `a4208261cfc5ee604eea287f0eb626d040d85862`. The only input-file change is an added final newline from the repository
editor. All JSON values and 77 cases are unchanged. Integrated file SHA256:
`a8aaa7b43ce0d7c2f5e8abe9bbc3994677bd68d4bbcbd4ba88c6b08b5c7c16f4`.

This integration was run against the separate main checkout at
`e8d7ed7298bca52f06c8fa547db5138b5e832384`, including the session-checked read
composition. The original `target_commit` in the JSON identifies the corpus's
creation baseline, not the current checkout or an approval of later changes.

Original pre-newline file SHA256:
`45bd0f8543011a4132eceb8c0dd4cfa49be2b700deeb6e1f1a7f94de902addb7`.

## Automatic execution

`test_adversarial_corpus.py` is discovered by the existing unittest command:

```sh
python -m unittest -q
python -O -m unittest -q
```

The runner has two unittest methods: one executes all 77 named subcases and
one checks the manifest's case count, ID uniqueness, schema and known kinds.
A failed case includes its stable ID. These are 77 declarative cases, not 77
standalone unittest methods. The complete current suite reports 331 methods.
No CI workflow, implementation module or dependency changes are required.

The integration removes the original standalone runner's CLI path argument
and resolves the JSON relative to the test module. The original assertion bodies
remain unchanged. Running discovery no longer consumes a unittest command-line
argument or mutates the import path.

## Covered behavior

- Local session UUID, account shape, personal scope, bank/country binding and
  expiry validation, plus private summaries and input non-mutation.
- Consent callback origin/path, state/code shape, duplicate/unknown query
  fields, encoding, TTL, one-use behavior and replay. Positive controls include
  a valid callback after wrong-state traffic.
- Read allowlist rejects another account/session, host/path confusion,
  authorization/payment routes, invalid/duplicate dates, unknown fields and
  malformed cursors before obtaining a token or invoking MockTransport.
- Pager HTTP failure states stop after one call without automatic retry.
  URL-like cursors remain opaque query values, not destinations. Successful
  synthetic pagination does not claim live data or complete history.
- Cooperative cancellation propagation and local session expiry.

Positive controls exercise accepted session creation, a permitted GET using
`httpx.MockTransport`, opaque cursor handling and valid consent. The suite
cannot pass simply by rejecting every input.

## What this does not prove

No actual provider network, JWT cryptography, account ownership, bank linking,
real consent/revocation, browser callback, TLS, Windows, physical device,
persistent-store ACL or network streaming was exercised. All identifiers,
codes, responses and account amounts are invented. The injected mocks do not
read credentials, create keys or register an application.

The low-level HTTP and session corpus is not a proof that a caller performs
live consent checks. The separate `test_provider_checked_session.py` covers
the isolated wrapper and the actual simulated pager's revocation-between-pages
case. That wrapper is still disconnected from the MCP and not an atomic
consent guarantee. Neither suite authorizes a real read or changes activation
gates. Independent review and CI apply to each exact remote candidate.
