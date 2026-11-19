# Security

This is an experimental local synthetic-data server. There is no production security support guarantee and no live bank adapter. All versions should be treated as prototypes until a supported release policy is published.

## Report a problem safely

Do not include credentials, bank statements, account identifiers, private keys, cookies, tokens or personal information in an issue, PR, screenshot or log. Start with a minimal synthetic reproduction and a general description of impact.

If this repository's Security tab offers private vulnerability reporting, use that route. Otherwise use an existing private maintainer channel you already know, without sending secrets. No private reporting address is promised here. Do not publish an exploit payload or a secret merely to ask for a private route.

If a credential has been exposed, revoke or rotate it with its issuer. Deleting the latest file does not remove git history, caches, forks or logs. Treat it as compromised until rotation is complete; do not rely on a history rewrite alone.

## Threat model and limits

The current server uses embedded invented fixtures, three read-only tools and local stdio. It does not load provider keys or offer a real-bank mode. Bank environment variables are ignored. An MCP client can still transmit tool results to an AI service. Review that client's privacy behavior independently.

Provider descriptions and remittance text are untrusted data. Tool annotations are hints, not authorization. The absence of write endpoints, destination constraints and validation provide the actual boundaries. Test fixtures with adversarial-looking text test data handling, not a guarantee about any AI client's behavior.

Experimental response normalizers, paginators and the opt-in HTTP/JWT library are not registered as MCP tools. The HTTP library is disconnected from the MCP and has no demonstrated live compatibility. Its diagnostic suppression changes logging handlers globally and must be reconsidered after logging reconfiguration. Each adapter call has a cooperative total deadline, including streaming, but no rate policy or multi-call request budget. See docs/HTTP-EXPERIMENT.md. A future transport must reject redirects, cap bytes while streaming, set connect/read deadlines, enforce authorized accounts and consent, limit requests and refuse mutation/payment endpoints. A coroutine timeout is not a hard process-level deadline when code blocks or suppresses cancellation.

Do not expose stdio through a public gateway or add real data without a separate access-control, privacy and operational review. No authentication, multi-user isolation, retention policy or production monitoring is supplied here. Never use synthetic balances as current facts or financial advice.
