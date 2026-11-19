# Final goals and release gates

The goal is a useful personal, local-first, read-only banking MCP, not a fixture demo forever. The current release is still synthetic-only. The goals below describe work to complete and verify, not features already available or a promised delivery date.

## 1. A real account-information connection

Connect the operator's own eligible bank accounts through Enable Banking's supported account-information flow. Read accounts, balances and transactions only. Use the provider's current ASPSP catalogue and the account's actual country, account type and institution before offering a connection.

Revolut is a target, not a compatibility guarantee for every account. Published coverage is a lead, not proof that a particular consent, account or date range works. Validate with a separately authorized end-to-end connection. Never substitute scraping, private mobile endpoints or a payment API.

## 2. Local custody and an explicit setup flow

For the Windows design, keep the private application signing key on the operator's own computer, nonexportable through the supported key store. Register only the corresponding public certificate. This is a proposed custody model, not a current tested feature or protection against malware running as the same user.

Before key creation or activation, verify runtime support, exact key identity, permissions, certificate policy, failure cleanup and recovery. Build a fixed-purpose in-process bridge to the trusted transport; do not print JWTs, pass them in shell arguments, write temporary token files or offer a generic signing service.

Show the final application name, description, privacy/terms URLs, contact, redirect and public-certificate identity before submitting registration. Registration and access consent are separate decisions. The account owner must complete the bank's own consent and Strong Customer Authentication. Never ask for the banking password in chat or repository configuration.

The proposed HTTPS loopback redirect remains unconfirmed for Production. A working local listener does not prove the provider accepts its URL or certificate. Validate that exact redirect through the supported flow; do not silently replace it with a public endpoint, tunnel or relay.

## 3. A reliable, bounded read path

After setup is approved, connect only the authorized, linked accounts to read endpoints. Preserve exact decimal strings, currency and date provenance, pending/booked distinctions and explicit incomplete-history limits. Enforce pagination bounds, deadlines, response-size limits, host/path restrictions, request budgets and refusal handling.

Keep real data and operational identifiers out of source, CI, screenshots and public diagnostics. Document actual private storage, retention and deletion before activation. Stop on expired or revoked consent. Reauthorization must use the supported flow. Deleting local configuration is not proof of bank-side revocation.

## 4. Useful analysis without invented conclusions

Make bounded search, grouped summaries, explainable recurring-pattern candidates and deliberate export useful over authorized data. Do not label a pattern as a confirmed subscription or fraud, predict charges without evidence, combine currencies, assume merchant identity or infer complete history from an exhausted cursor.

The current CSV and recurrence modules are isolated library functions. Wiring them to real account data needs its own review; their presence does not imply that integration is complete.

## 5. Reproducible operation and visible evidence

Provide a short installation and verification path, a no-secret local receipt and clear failure/recovery instructions. Keep the synthetic demo for development and testing. Make synthetic and live results unmistakable, including source, observation time and limits.

Use focused PRs, independent review at the final remote head and green checks before merging. Test Windows-specific behavior on Windows. Synthetic tests and compilation elsewhere do not prove Windows key custody, live compatibility, security audit completion or regulatory approval.

## Release gates

| Gate | Evidence required | Current position |
| --- | --- | --- |
| Synthetic MCP | Real local MCP session and negative tests over invented data | Implemented; five fixture tools |
| Windows signer | Windows compilation, key-policy/ACL checks, identity binding, negative tests and cleanup proof | In preparation; no completed Windows execution claim |
| Redirect | Local TLS/callback checks and provider acceptance of exact registered URL | Provider acceptance unresolved |
| Registration | Final visible form and explicit operator approval | Not registered by this project workflow |
| Account linking | Owner's bank consent/SCA and each intended account explicitly linked | Owner step, not performed by software maintainers |
| Live read integration | Authorized account/balance/transaction reads with provenance and failure handling | Not connected to the MCP |
| Operational use | Reviewed storage, revocation, recovery, limits and clear live/demo separation | Not production-ready |

## Permanently outside scope

Payments, transfers, trading, FX execution, payee or card changes, access to another person's accounts without authority, generic HTTP/shell/file tools, a public multi-user banking service and claims of bank/provider endorsement. Any paid agreement or wider service deployment is a separate decision. The code license does not grant provider access or regulatory permission.
