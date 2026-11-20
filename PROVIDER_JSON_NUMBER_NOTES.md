# Provider JSON finite-number boundary

The experimental transaction pager, checked-session reader and separate admin setup response now share one strict JSON decoder. No live provider or bank connection was made for this change.

Python's JSON parse_constant callback rejects literal NaN and Infinity, but does not intercept exponent overflow such as `1e999` or `-1e999`. Previously a nested extra field containing one of those numbers was accepted as an infinite float, even when the normalized financial fields were valid strings. The pager could report a complete synthetic page, the session checker could continue to an account request and the admin exchange could return a private reply containing that nonfinite extra.

The shared decoder adds parse_float with an explicit finite check. Duplicate keys, literal nonfinite constants and exponent-overflow numbers are rejected at any nesting level. Pager/session/admin retain their existing safe error boundaries, no retry and no partial-result behavior. A failing session check never starts its account request. A failing second transaction page never returns a partial first page.

Finite numeric extras remain allowed under the existing schema and are discarded where they were discarded before. This is not arbitrary-precision numeric normalization: financial amounts must still be bounded decimal strings. No money field, rounding rule, endpoint, allowlist, request budget, consent logic, logging policy or MCP tool changes.

Eight new test methods use injected synthetic transports, including an httpx MockTransport for admin responses. They exercise exponent overflow/literal nonfinite values nested in ignored extras, finite-value controls, duplicate keys, second-page failure, session refusal before account reads and safe errors. No real HTTP, credentials, bank session, Windows key or application registration is used. Local Python results do not establish Windows or live-provider compatibility.
