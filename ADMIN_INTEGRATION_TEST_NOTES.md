# Synthetic admin integration suite

Original MIT test code, copyright2026 Marco Antonio Tevar Asensio. No new dependencies or external source copied. Uses existing separately attributed Apache admin_consent and MIT project modules. Preserve all accumulated upstream licenses/notices when assembling the test tree.

Five integration tests connect the proposed modules rather than testing each in isolation:

1. Construct an offline ConsentAttempt and personal authorization body.
2. Send POST/auth through httpx.MockTransport, never the network provider.
3. Send a reconstructed callback over a real ephemeral127.0.0.1 TCP socket, consume state exactly once and receive the private code body.
4. Exchange the code through MockTransport POST/sessions.
5. Validate bank/country/expiry/UUIDs with provider_session.
6. Persist only the minimal synthetic session identifiers/expiry through the private POSIX store in a temporary directory.

Negative paths prove wrong callback state does not reach exchange or storage, mismatched bank and invalid account list do not persist anything, and replay cannot reconnect to the closed receiver or create another session request. The success test captures debug logging/stdout/stderr and public callback response/constant reprs, then checks that state/code/IBAN/JWT/session/account canaries are absent. The stored data is inspected privately and contains no IBAN. A session summary still reports live consent not verified. Fixed synthetic identifiers are not real account data.

## Run

Place reviewed modules at the import root: admin_consent, admin_http, callback_framing, callback_receiver, provider_session, private_store, provider_http and provider_pager. Use the project's pinned dependencies. Then run `python -m unittest -v test_admin_integration_synthetic` and `python -O -m unittest -v test_admin_integration_synthetic`.

This suite depends on the separately reviewed module packages. It is not a standalone replacement for those modules or permission to override newer reviewed versions. If modules move to a package during integration, update imports and rerun the complete suite/CI at the actual new commit.

## Evidence boundary

Five tests pass normal and optimized Python on POSIX. This proves only the synthetic in-process orchestration with real local TCP and temporary private files. No real Enable Banking request, application, key, user authorization, bank data, SCA, Windows certificate/trust store, HTTPS/browser callback, SSH tunnel or server deployment was exercised. The complete real workflow remains gated on provider redirect support, reviewed Windows implementation, owner decisions and successful end-to-end validation. These tests do not grant permission to enable a provider or add admin methods to the MCP tool set.

Coverage limit: this integration suite does not directly test expiry of the callback TTL. Existing module unit tests cover local expiry behavior, but they are not a substitute for an end-to-end TTL test or any live banking, TLS, SSH, Windows or active-consent validation.
