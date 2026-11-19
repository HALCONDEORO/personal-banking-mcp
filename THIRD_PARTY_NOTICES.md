# Third-party notices

## Python MCP SDK

https://github.com/modelcontextprotocol/python-sdk

Dependency, not vendored code. License text from installed mcp 1.30.0:

MIT License

Copyright (c) 2024 Anthropic, PBC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


Other installed packages retain their respective licenses. Full dependency review is required before release. No source code from the design-reference repositories was copied.


## EU Open Banking MCP money invariants

- Repository: https://github.com/cver-me/EU-Open-Banking-MCP
- Commit: `2c69f420c0dd20ecbdd65172538644f928df5cb5`
- Source: `src/lib/money.ts`
- Source URL: https://github.com/cver-me/EU-Open-Banking-MCP/blob/2c69f420c0dd20ecbdd65172538644f928df5cb5/src/lib/money.ts
- License: MIT, original in `LICENSES/EU-Open-Banking-MCP-MIT.txt`.
- Original copyright: Copyright (c) 2026 personal-finance-eu-mcp contributors.
- Adapted file: `test_money_corpus.py`. Adapted the bounded-input, independent-decimal-context, exact decimal-string, no rounding and unsigned-zero invariants into Python regression cases. No TypeScript runtime or decimal.js dependency was imported. The existing normalizer deliberately preserves source scale and does not adopt upstream minimum minor-unit padding or its unknown-currency two-digit fallback. No totals, currency conversion or aggregation were added.
- Modifications dated 2026-11-19: Marco Antonio Tevar Asensio.

## Tesco grocery MCP observation metadata

- Repository: https://github.com/HALCONDEORO/tesco-ie-grocery-mcp
- Commit: `08db94c5230ab74d9a573415442e22a5961e5c69`
- Source: `src/provenance.mjs`
- Source URL: https://github.com/HALCONDEORO/tesco-ie-grocery-mcp/blob/08db94c5230ab74d9a573415442e22a5961e5c69/src/provenance.mjs
- License: MIT, original in `LICENSES/tesco-ie-grocery-mcp-MIT.txt`.
- Original copyright: Copyright (c) 2026 Marco Tevar.
- Adapted file: `provider_provenance.py`. Ported the observation timestamp, uncertainty and untrusted-content metadata structure to Python; removed retail market/store/pricing data and arbitrary source URLs. Added explicit synthetic/provider-response labels, timezone validation and unknown history/freshness/reconciliation status. No account IDs, cursor, authorization data or provider text enter this helper.
- Modifications dated 2026-11-19: Marco Antonio Tevar Asensio.

`provider_normalize.patch` modifies existing project code and retains its project MIT license. `patch-base.json` records the exact observed main revision. Apply the minimal patch only after verifying its base/context; do not replace newer normalizer changes blindly. The full patched normalizer is included for reviewer execution, not as authority to overwrite remote changes.
