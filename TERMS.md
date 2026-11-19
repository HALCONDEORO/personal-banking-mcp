# Software use and provider conditions

General software information, not legal advice.

## Code license

The project source is provided under the MIT license in `LICENSE`. Third-party components retain their own licenses and copyright notices, documented in `THIRD_PARTY_NOTICES.md` and the dependency packages. Nothing here grants rights to another party's trademarks, APIs, bank data or services.

The software is experimental and provided as-is, without warranty, on the terms of the MIT license. It is not financial advice, a bank, a regulated account-information service, or an official Revolut or Enable Banking product. No affiliation or endorsement is claimed.

## Personal read-only purpose

The default version is a synthetic-data demo. Real bank access, if separately implemented and enabled, is an explicit additional setup step, not a prerequisite to trying the project. No payments, transfers, foreign-exchange execution, payee changes, card administration or generic network tools are within the project's scope.

You must use only accounts you are authorized to access and only for the purpose the account owner approved. Bank consent must be obtained through the bank/provider's supported flow. Never give your bank login password to this software's maintainers or paste it into an AI conversation.

Read-only access can still expose sensitive information. You choose the AI/MCP client receiving tool outputs and must consider that client's data handling before sending financial data to it.

## Enable Banking is a separate service

Enable Banking's registration, terms, privacy notice, account eligibility, API limits and bank consent requirements apply independently. At the time of preparing this project, Enable Banking described free restricted-production access to a private individual's own linked accounts for personal, non-commercial use. That is not a promise of perpetual free service or permission to operate a business, hosted aggregator or multi-user application.

Dashboard account linking and authorization of an application session are different steps. A provider application or signing key does not authorize a bank consent by itself. A read-only application may need specific setup authorization requests, but payment endpoints are not needed and must not be exposed to the MCP.

Check the current provider terms before enabling access. If your intended use falls outside personal restricted use, obtain the appropriate agreement from the provider first. This source-code license does not sublicense provider access or establish a regulated status.

## Responsibilities and safety

Use private configuration and secret storage outside the repository. Do not publish real financial examples, private keys, tokens, bank/session/account identifiers, authorization codes or diagnostic URLs. Keep software updated, review dependencies and restrict the deployment's network and filesystem access.

Account information can be delayed, incomplete or unavailable. Pending entries, booked entries, internal transfers, refunds and multiple currencies require care. An exhausted API cursor is not proof of complete financial history. Do not rely on this prototype alone for tax, accounting, legal or financial decisions.

Stop on revoked or expired consent and reauthorize through the supported provider flow rather than bypassing a bank check. Follow provider limits and do not use scraping or reverse-engineered personal-bank endpoints as a substitute.

## No service commitment

The repository does not provide a managed banking connection, support contract, uptime commitment or guarantee that a particular bank account is compatible. The operator controls their deployment and any necessary deletion or consent revocation. No subscription, paid plan or financial obligation is created by using the synthetic demo.

Official terms: https://enablebanking.com/terms/ . Privacy information for this software is in `PRIVACY.md`.
