# Test bank: personal-banking-mcp (read-only, fixture-first)

Scope: the MCP is read-only over synthetic fixtures. No real bank, no keys,
no real data. Current product contract (PR #1, head 6fc5be6): Python,
FastMCP (mcp<2 API), stdio; tools list_accounts, get_balance,
get_transactions(account, start, end, limit=20, offset=0); response envelope
{source, live, as_of, data, next_offset, complete}; synthetic fixtures
(demo-eur/demo-gbp, January 2026); amounts are signed decimal strings.

## Runners (all require SERVER_CMD; a mock PASS is not a product PASS)

1. **Property tests** (`tests/properties.mjs`, fast-check, FC_SEED)
   - P1 offset pagination reassembles the full filtered set, order-stable.
   - P2 every returned date inside [start, end] (window derived from as_of).
   - P3 read-only idempotence.
   - P4 known account MUST succeed; arbitrary ids give structured errors;
     health = successful list_accounts with parseable payload.
   - P5 arbitrary start/end/offset: structured error or valid page, no crash.
   - P6 large offsets: structured error or empty complete page, no loop.
   - P7 synthetic canaries never in captured server stderr (checked against
     captured output, never by scanning source - tests/docs contain canaries
     by design).

2. **Fuzz corpus** (`fuzz-corpus/accounts.json`, `transactions.json`;
   runner `tests/fuzz.mjs`; `{KNOWN}` and the account parameter name are
   resolved against the live server schema)
   - URLs as account: https/http/localhost/127.0.0.1/10.x/192.168.x/
     169.254.169.254/userinfo/redirector/file://, traversal, absolute path,
     empty, foreign, SQL-ish, shell-ish, NUL; extra unknown field.
   - Pagination: negative/float/string offset; NaN/negative/zero/float/
     string/enormous limit (valid start/end supplied so the tested arg fails).
   - Dates: inverted period, month 13, Feb 30, NaN, Infinity, datetime+tz,
     URL as date; foreign account; unknown-tool probes (make_payment,
     http_request) must error and leave the server healthy.

3. **E2E client check** (`e2e/mcp-client-check.mjs` + `e2e/product.mjs`)
   Discovers the account parameter name and envelope shape from the live
   schema. 35 checks: tool surface (exactly the 3 tools, no payments/http),
   happy path with offset pagination (loop-guarded, strictly increasing),
   signed-amount shape, inert instruction/URL data, date filter, all
   negatives above, unknown-tool robustness, idempotence, canary hygiene.

4. **CI** (`.github/workflows/node-suite.yml`, additional job; the product's own ci.yml stays untouched)
   permissions: contents: read; no secrets; SHA-pinned actions/checkout
   v7.0.1, setup-python v7.1.0, setup-node v7.1.0; env SERVER_CMD=python3,
   SERVER_ARGS=server.py; steps: pip install -r requirements.txt, pip check,
   npm ci, properties (FC_SEED=run id), fuzz, e2e. Canary hygiene asserted by
   runners against captured stderr only.

## Verified results (2026-11-19 ~19:09 WET, Node 22 + Python 3.10, mcp 1.x)

v6 - product-only. Verified against the byte-verified source of PR #1 head
bc3355c (HALCONDEORO/personal-banking-mcp): tar SHA256
5a085b6b1538649926b95387ee1d27fa5954effe0a05da91887d7c6bc8feb6f0, all 15
tree hashes match, server.py identical to 6fc5be6 except one trailing blank
line; the bc3355c delta is copyright-only (LICENSE/LICENCIAS/READMEs now
name Marco Antonio Tevar Asensio).

- product's own unittest: 29/29 OK
- properties: 9/9 (P0 non-empty precondition; P8 default limit == 20;
  P9 complete-flag invariant)
- fuzz: 55/55 + injected-canary check (boundary cases: limit 100/101,
  offset 10000/10001, 366/367-day spans, missing/null/array/numeric/bool
  args, 5000-char and unicode accounts)
- e2e: 49/49 (new: A3 readOnly/destructive/idempotent/openWorld
  annotations on all 3 tools; B11 list_accounts never leaks balances;
  B12 complete flag consistency; B13 default limit; C7 offset == size gives
  empty complete page; D14-D22 missing/null/array args, 366/367-day
  boundary, long and unicode accounts)

v6 product behaviors confirmed at the boundary: 366 inclusive days allowed,
367 rejected; limit 100 allowed, 101 rejected; offset 10000 allowed, 10001
rejected; default limit equals 20; all tools carry readOnlyHint annotations.

Delivery: suite attached for PR #2 (via Server). Canary run uses mkdtemp +
finally cleanup. CI adds only .github/workflows/node-suite.yml; the
product's Python ci.yml stays untouched.
