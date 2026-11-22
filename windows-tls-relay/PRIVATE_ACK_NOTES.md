# Private duplex ACK proof, synthetic only

This fixture tests a private parent/child acknowledgement exchange. The actual .NET LocalTlsRelay parser canonicalizes an invented browser request; the actual Python ConsentAttempt validates its state and consumes it once; the .NET child then builds the actual fixed LocalTlsRelay.Response. Python checks those bytes against callback_framing.response_bytes. No socket, TLS host, certificate/store, provider, session write, MCP tool, owner laptop or real callback is involved. The existing production-unready loopback path is unchanged.

## Ordering differs from the one-way data proof

PR57's one-way proof requires child EOF, exit and cleanup BEFORE consumption. That is deliberately not possible for this interactive ACK: the child must stay alive to receive the parent's decision. Here the order is bounded target frame, local validation/one-use consumption, deadline recheck, ACK plus input EOF, fixed response frame, output EOF, exit zero, verified direct-child cleanup, final deadline check, receipt. Do not reuse PR57's exit-before-consume claim for this code.

The returned receipt contains a boolean and fixed synthetic response bytes, never a code or provider session body. A positive boolean means the invented callback was validated locally. The response explicitly says a bank session is not confirmed. A negative receipt means local validation rejected the callback, not a diagnosed provider error. No browser received anything: this fixture transports browser-response bytes privately back to its parent.

Once the attempt is consumed, ACK failure cannot roll it back. The child may already have received a positive ACK or produced response bytes before nonzero exit, timeout, malformed trailing output, cleanup failure or caller cancellation. In those cases no receipt is returned. Sent bytes cannot be retracted; consumption cannot be undone. Do not automatically retry or claim a browser saw either success or failure. The fixture has no provider side effect. A future integrated host must define its own uncertain-outcome and browser-disconnect handling.

## Bounded protocol and trust

- Input: PAI1, big-endian uint32 length, 1..12288 bytes of invented browser HTTP. Input stays open for ACK. The parser rejects malformed headers/Host/targets using the existing implementation.
- Child target: PAD1, big-endian uint32 length, canonical ASCII target at most 8192 minus the fixed origin length. Parent validates the direction, size, encoding and prefix before ConsentAttempt.
- ACK: exactly PAA1 and one byte (0 rejected, 1 locally validated), then input EOF. Missing, truncated, unknown-value, wrong-magic, trailing or duplicated ACK produces no response frame. The child waits for EOF before generating response bytes.
- Child response: PAR1, big-endian uint32 length, 1..1024 bytes. Parent requires the exact pre-existing fixed response matching its own decision, exact output EOF, exit zero and successful cleanup before returning a receipt.

This is a trusted bundled synthetic child, not an adversarial peer. Target frames cannot be proven final before interactive consumption: a malicious child can send extra frames or lie before it exits. The parent detects unexpected response/trailing output and withholds the final receipt, but that does not undo earlier consumption/ACK. No cryptographic peer attestation, installation/hash enforcement, hostile-same-user isolation or owner-laptop handle-security qualification is claimed. A future host needs a separately reviewed trust and framing contract.

The fixed absolute runtime and assembly path, allowlisted synthetic modes, sanitized environment and inherited pipe handles follow relay_process. Only the direct child is reaped. Acquisition and cleanup can outlast the protocol deadline; no Job Object, descendant containment or kernel hard deadline is claimed. Cancellation during spawn recovers the child; repeated cancellation cannot interrupt the separate shielded cleanup task. Failures are generic and stdout/stderr do not expose callback values. This does not promise secrecy from debugger locals, process dumps or hostile code under the same user.

## Tests

Build Release, then run `python windows-tls-relay/test_callback_ack.py` and `python -O windows-tls-relay/test_callback_ack.py` with CONTROL_TEST_DOTNET pointing to an explicit trusted .NET runtime. The entry point requires at least 31 tests and zero skips. The Windows TLS workflow runs both modes on real child processes. Native receipts must be inspected at the exact PR tree; local Linux evidence is not Windows qualification.

The suite exercises actual parser/consent/ACK/response round trips, percent encoding, denial, wrong state and Host, consume-before-ACK ordering and replay rejection, both ACK values, missing/truncated/duplicate/invalid ACK, request/data/response framing, early/nonzero exit, no response before ACK (a bounded observation, not an all-timing proof), expiry before data/after consumption/after ACK/after cleanup, repeated cancellation, spawn and cleanup faults, one-use/no automatic retry, closed attempts/reaped children, generic errors and no echoed values. Fault injection supplements real processes; it is not a production integration test.

Remaining: production host/private transport integration, truthful browser delivery and uncertain-outcome semantics, process/handle/install custody qualification, target-laptop review, provider Production redirect support, registration, owner consent, and a separately authorized live read adapter. No real-bank readiness follows from this proof.
