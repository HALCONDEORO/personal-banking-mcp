# Integration state: code, proofs and missing joins

Repository snapshot after PR59, 22 November 2026. This is a map of existing
implementation, not an installation or activation procedure. The released MCP
still serves invented fixtures. There is no live-mode switch, real-bank result,
owner-laptop qualification or promised connection date.

## What actually exists

| Boundary | Code and evidence | What it does not prove |
| --- | --- | --- |
| MCP presentation | [`server.py`](../server.py), [`demo.py`](../demo.py), [`test_demo.py`](../test_demo.py) | Five read-only tools and a real local stdio walkthrough over invented data, not a bank adapter or connected dashboard |
| Browser TLS parsing and fixed local hop | [`LocalTlsRelay.cs`](../windows-tls-relay/Relay/LocalTlsRelay.cs), [`SyntheticTests`](../windows-tls-relay/SyntheticTests/Program.cs), [native TLS notes](../TLS_SYNTHETIC_CI_NOTES.md) | A library plus synthetic harness, not an owner-ready executable; current forwarding is still fixed HTTP loopback and is not local-process authentication |
| Python callback validation/lifecycle | [`callback_framing.py`](../callback_framing.py), [`callback_receiver.py`](../callback_receiver.py), [`admin_consent.py`](../admin_consent.py), [supervisor](../windows-tls-relay/SUPERVISOR_NOTES.md) | State/one-use/TTL and cooperative cleanup, not a provider session, a Windows process host or a kill deadline |
| Private child control | [`relay_process.py`](../windows-tls-relay/relay_process.py), [control notes](../windows-tls-relay/PRIVATE_CONTROL_NOTES.md) | Fixed synthetic child startup/stop and direct-child reaping, not a launched production TLS relay, Job Object or descendant containment |
| One-way private callback data | [`callback_pipe.py`](../windows-tls-relay/callback_pipe.py), [data notes](../windows-tls-relay/PRIVATE_DATA_NOTES.md) | Actual parser/ConsentAttempt joined through bounded inherited pipes, but only fresh invented callbacks; no TLS socket or browser ACK |
| Duplex private ACK | [`callback_ack.py`](../windows-tls-relay/callback_ack.py), [ACK notes](../windows-tls-relay/PRIVATE_ACK_NOTES.md) | Actual parser/ConsentAttempt/fixed response joined through pipes; no real browser delivery, TLS host integration or provider-session confirmation |
| Signing-to-read seam | [`signer_seam.py`](../signer_seam.py), [bridge contract](../LOCAL_BRIDGE_CONTRACT.md) | Fixed token-shape adapter only, not signature verification, an implemented Windows signer backend or provider acceptance |
| Read checks and storage | [`provider_checked_session.py`](../provider_checked_session.py), [Windows store limits](../WINDOWS_PRIVATE_STORE_NOTES.md), [personal readiness](../PERSONAL_SETUP_READINESS.md) | Separately tested components, not a joined live MCP read path, owner-laptop ACL qualification, storage/recovery acceptance or current bank consent |

## Three different callback proofs, not one completed bridge

1. **TLS/HTTP loopback:** the existing relay accepts one synthetic TLS connection,
   parses browser input, forwards a rebuilt request to the fixed Python backend,
   and accepts only the expected constant backend response. The fixed address
   and Host do not authenticate a competing local process. Its native tests use
   generated synthetic certificate/key material and exact cleanup, not the
   owner's signing key or browser trust settings.
2. **One-way DATA:** the parent requires one complete target frame, output EOF,
   child exit zero and verified cleanup **before** consuming ConsentAttempt.
   This is possible because that child does not wait for a decision. It says
   nothing about how a browser receives a response.
3. **Duplex ACK:** the child must remain alive to receive ACK. The parent consumes
   the invented attempt first, rechecks its deadline, sends one fixed decision
   plus input EOF, then verifies the fixed response, output EOF, zero exit,
   cleanup and deadline before returning a receipt. It cannot inherit the DATA
   proof's exit-before-consume claim. After ACK, failure cannot unconsume the
   attempt or retract bytes already sent. No automatic retry is safe merely
   because no final receipt was returned.

Both private-pipe proofs trust the runtime, bundled assembly and installation
path. They are not cryptographic peer attestation or a security boundary against
hostile code running as the same user. The interactive proof cannot establish
malicious-child frame finality before consumption. A response-byte receipt is
not a browser-delivery receipt. These limits matter before replacing the HTTP
hop; the existence of a private fixture does not replace that hop by itself.

## A traceable native snapshot

PR59's reviewed published head was
`19e9ef0469d910d27e19c294a3b99b0eae02ca06`. Native pull-request CI checked out the
automatic merge ref `2419369f93d8b3ddc06f704693062bd89d3f6a69`, not the same commit.
The merged main commit is `a3f248a04538ed926d86454902a0b730dc69112b`. All three have
the same complete tree `ce9df52b8c6bea20fbcacbebeaf6f70d00db86f3`, verified by a
whole-tree diff. This is a pinned historical snapshot, not a claim about all
future heads or all supported Windows versions.

- [Native TLS/process job](https://github.com/HALCONDEORO/personal-banking-mcp/actions/runs/45066289902/job/137343060509): Windows Server 2025, CPython3.12.10, .NET SDK10.0.404; control17+17, DATA28+28 and ACK31+31 normal/actual `-O`; Debug/Release key A/B10+10 and TLS75+75, with named-key cleanup before PASS. Release fixture builds reported zero warnings/errors.
- [Native portable job](https://github.com/HALCONDEORO/personal-banking-mcp/actions/runs/45066289913/job/137343060975): 382 normal and382 optimized Python tests, both passed without skips.
- [Reviewed and merged PR59](https://github.com/HALCONDEORO/personal-banking-mcp/pull/59): separate synthetic ACK proof; no production host, bank connection, new token or permission.

Counts identify those runs, not a permanent minimum for unrelated suites.
Read the actual final-tree commands and results when reviewing a later change.
Hosted-runner evidence does not qualify the operator's laptop, account, browser,
certificate trust, key ACLs or complete consent route.

## Next implementation gates

- Join an explicitly trusted TLS host with the private callback protocol, without
  quietly leaving an unauthenticated fallback or adding arbitrary destinations.
- Define browser response/delivery, cancellation, deadline and uncertain-outcome
  behavior. A locally validated callback is not a created bank session. A
  disconnected browser or failed ACK does not authorize replay of a consumed
  attempt or automatic retry of a consent-changing provider request.
- Qualify direct-child/process-tree expectations, pipe handles, installation
  identity, certificate/key custody and storage on the intended Windows system.
  Synthetic generated keys are not the application's actual signing key.
- Join signing, authorized session checks, the exact selected account allowlist,
  protected storage and the read transport before exposing real reads to MCP.
- Separately resolve provider-supported Production redirect and device return,
  final registration, linked accounts, owner-completed SCA/API consent, recovery
  and revocation. [Readiness](../PERSONAL_SETUP_READINESS.md) records those gates;
  it is not permission to execute them.

The API signing certificate and TLS localhost certificate have different roles.
Control Panel linking and API consent are separate. The phone's localhost is not
the laptop. Keep those boundaries visible while adding integration, rather than
turning a successful fixture into an unsupported activation instruction.
