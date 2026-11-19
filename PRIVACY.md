# Privacy information

General software information, not legal advice.

This page describes the open-source Personal Banking MCP software, not a hosted financial service. Read it together with the version you actually install and the notices of the services you choose to connect.

## Current default: synthetic data

The default MCP demo uses invented accounts and movements. It does not access a bank. No real financial information is needed for installation, tests or CI.

Optional provider modules are experimental until their integration is reviewed and documented. The presence of those modules does not mean a live bank connection is enabled.

## A personal deployment

A person who separately enables bank access runs their own private deployment and chooses its configuration. The source-code maintainers do not operate a shared bank-data service, receive users' application keys, or administer their bank consents through this repository.

A personal deployment may process account balances, transaction dates, amounts, currencies, statuses and descriptions. Account/session identifiers and application signing keys are private operational state. They must remain outside the source repository, examples, issues, CI and public logs.

Use a dedicated operating-system identity or container and private storage, separate from customer or business data. Restrict secret files to the deployment owner. Publishing source code does not authorize publishing its configuration or financial data.

## Third parties and AI clients

If you choose Enable Banking, it is a separate provider between the deployment and your bank. Its terms and privacy notices apply independently. You authenticate at your bank and grant a revocable account-information consent. This project does not need your banking password and does not provide payment functionality.

Your selected MCP/AI client receives the outputs of the tools you call. If that client uses a remote AI service, financial information in those outputs may reach that service under its own terms. Running the MCP on your own machine or private server does not by itself make the AI client offline.

## Storage and logs

The synthetic demo has no financial cache or telemetry. Any later live adapter must document its actual retention and deletion behavior before activation. Private keys, authorization codes, tokens, session IDs, account identifiers, full request URLs and bank-response bodies must not be printed to application logs or diagnostics.

If an operator enables a live setup callback, it must use a short-lived, state-bound authorization flow with no query logging, analytics or caching. Operational state must not be committed to GitHub. This page alone does not implement those protections.

## Choices and removal

You can stop the process, remove local/private configuration and revoke bank access using your bank or provider's supported controls. Deleting this repository or removing the MCP from a client does not necessarily revoke an existing bank consent. A provider may retain information under its own policy.

Do not upload statements, bank identifiers or secrets to GitHub issues or pull requests. Security reports should omit private data and use the repository's private reporting channel when available. For Enable Banking's own data processing, contact Enable Banking through its published privacy channels.

## Limits

This is a general description of a self-hosted open-source project, not a substitute for an operator's privacy obligations. A hosted, commercial or multi-user deployment requires its own assessment and provider agreement where applicable. This page does not promise GDPR compliance, provider approval or regulatory authorization.

Provider website/Control Panel privacy notice and API terms; consult the notices shown during any bank-consent flow too: https://enablebanking.com/privacy and https://enablebanking.com/terms/ .
