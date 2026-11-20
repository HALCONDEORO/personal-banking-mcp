# Personal-use setup readiness, not an activation procedure

Checked against the official Enable Banking pages on 20 November 2026. This
checklist does not create an application, accept terms, link an account, generate
a key, open a listener or make an API request. The released MCP remains a
synthetic-data demo. The Windows signing bridge and real-bank activation are
not implemented by this document.

## 1. Confirm the permitted use

The provider's current Terms allow free Control Panel/API use within their
scope. Production access under those Terms is restricted to linked accounts
for evaluation or private individuals' personal use. It is not permission for
commercial operation, business-account access, other people's accounts or a
shared provider application/key. Account limits may apply. The evaluation
exception for businesses is not a permanent right to commercial use. [1]

The FAQ says an application cannot be made available to the public before a
contract is signed. Publishing source code for a synthetic demo is distinct
from offering access to a registered application or sharing its credentials.
Do not infer that a public repository authorizes a shared bank connector. [2]

Before any real setup, confirm that the intended operator, account ownership
and use fit the provider's current terms. Stop for a separate agreement if the
intended use falls outside them. No price or eligibility promise follows from
this checklist.

## 2. Prepare registration without submitting it

The Control Panel documentation distinguishes Sandbox from Production. For
Production relying on Enable Banking authorization it lists the application
name, description, data protection email, privacy-policy URL, terms URL and
whitelisted redirect URLs. The displayed form is the final source for the
exact current requirements. [3]

Review the final visible fields, selected environment, public certificate,
key-custody plan and effects with the operator before pressing Register.
Approval of draft text is not approval to submit. Do not choose browser key
generation if the approved design requires a nonexportable Windows key.
Never put a private key, JWT or bank credential in the form's description,
repository, issue or screenshot.

A form accepting a string does not prove the provider supports the redirect
in Production. The proposed `https://localhost:8765/callback` is still an
unverified candidate, not a supported deployment instruction. A local listener
working in a synthetic test does not resolve this question. [3, 5]

## 3. Keep account linking and API consent separate

A newly registered Production application is inactive. The provider describes
restricted activation by linking the operator's own accounts. Restricted mode
exposes only those specifically linked accounts. Linking one account does not
authorize all accounts at that bank. [2, 4]

The provider explicitly says Control Panel linking does not perform API
authorization on the application's behalf. A separate API authorization flow
is still needed, including when using the same account. [4]

The operator completes bank login, SCA and consent through the supported bank
flow. No test result or registration draft replaces that decision. Do not
perform account linking or a consent-changing request from this checklist.

## 4. Select the actual ASPSP and country

Use the provider's current ASPSP catalogue and select personal PSU scope where
supported. An integration listing is a discovery aid, not proof that a
particular account, account type or consent route will work. [5, 6, 7]

Do not infer bank country from residence, phone country or an old example.
Retain the exact selected ASPSP/country and verify them against later session
responses. The selected personal accounts remain a local allowlist; a larger
provider response must not silently widen it.

The Ireland market page lists Revolut and describes app-based SCA. It also
states that credit-card accounts are selectable only in the Revolut mobile
app consent flow, not its web consent flow. This is provider documentation,
not a verified result for an operator's own Revolut account. [6]

## 5. Resolve the device-return problem before real consent

The quick start describes redirects carrying a code and the supplied state.
The callback must validate state and reject an unsolicited, duplicated or
expired callback. Treat the code and full callback query as private. Do not
paste them into chat, a public ticket, an issue or a screenshot. [5]

A mobile browser's localhost refers to that phone, not a Windows laptop. If
SCA changes device or browser, returning to a laptop-only listener may fail.
The FAQ warns that app switching may return to a different browser. Prove the
complete supported desktop/mobile return route without weakening TLS or
exposing the listener, before presenting consent as ready. [2, 5]

Do not silently replace the approved redirect with a cloud relay, tunnel,
public host, new certificate trust root or different storage service. Each
changes the security/data path and needs its own review and authority.

## 6. Gate any future read path

Required evidence before an operator-approved real read:

- Target Windows receipt, key custody, intended ACLs, cleanup and replacement
  tested. A Linux compile or a synthetic callback is not this evidence.
- Final registration and public certificate explicitly approved and verified.
- Provider-supported Production redirect and actual device return verified.
- Exact linked account set and separate API consent completed by the operator.
- A current authorized personal session with matching ASPSP/country/accounts
  and future local/provider expiry. Recheck before each account page.
- Read transport restricts host/path/query, redirects, response sizes, time,
  errors and logs. No automatic retry on throttling or consent failure.
- Storage, revocation, recovery, rate limits and necessary disclosures reviewed.

`CheckedSessionRead` is one isolated preparation component for the session
check, not completion of these gates. Revocation can race a successful check;
its synthetic tests do not prove an atomic or continuous authorization state.

## Sources and remaining uncertainty

[1] Terms of Service, last updated 8 January 2026, read 20 November 2026:
https://enablebanking.com/terms/

[2] FAQ, public availability, restricted activation and app-switch limitations:
https://enablebanking.com/docs/faq/

[3] Control Panel overview, registration fields and activation modes:
https://enablebanking.com/docs/api/control-panel/

[4] Own-account linking, restricted access and separate API authorization:
https://enablebanking.com/docs/api/linked-accounts/

[5] Quick start and API reference, ASPSPs, redirects and session protocol:
https://enablebanking.com/docs/api/quick-start/
https://enablebanking.com/docs/api/reference/

[6] Ireland market specifics, Revolut SCA and credit-card consent scope:
https://enablebanking.com/docs/markets/ie/

[7] Ireland integration catalogue:
https://enablebanking.com/open-banking-apis?country=IE

These pages establish documented behavior, not an approval, a legal opinion,
a working Production loopback route, physical-device compatibility or a
connection date. Recheck the terms, catalogue, form and relevant policies
when an actual setup is proposed.
