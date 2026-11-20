# Callback adversarial corpus integration

The original independent package targets `83cbcb1c3cf3e572d30520e7d1adb47080242254`.
Its JSON is retained at `tests/data/callback-contract.json`, outside the Node
MCP fuzz directory because that runner expects a different array schema.

The root `test_callback_adversarial_corpus.py` runs in normal unittest discovery.
The standalone checkout argument/import-path mutation is removed; the corpus
path is relative to the test module. Ten original test methods are retained,
plus a guard requiring 29 vectors, unique IDs and literal boolean verdicts.
The guard does not prove semantic identity if cases are deliberately replaced.

## What runs

- Actual Python framing parser, builder and constant-response function.
- 29 named declarative vectors, every strict prefix of a canonical request,
  target-size boundaries and every two-chunk split of a valid request.
- Actual `CallbackReceiver._handle` directly with synthetic reader/writer
  objects, not sockets. Positive delivery, malformed then good then replay,
  cancellation/inconsistent futures, busy/connection budget, trailing bodies,
  pipelining, truncation, oversize and reversed chunks.
- Actual consent validation for matching-state invalid code consumption.

This is 11 unittest methods, not one method per vector, prefix or split. The
captured results count unittest methods, not every loop iteration. The JSON's
original `target_sha` is provenance, not an approval of a later checkout.

## Deliberate limits

No call to receiver.start(), listener, real TCP EOF/half-close, TLS, browser,
Windows, signer, FFI/IPC, key/certificate, bank, provider exchange, stored
session, setup activation, host/SSH or external network. Fake drain finishes
immediately, so this does not prove backpressure/slow-peer cleanup. Directly
injected inconsistent lifecycle flags are adversarial handler inputs, not an
end-to-end workflow or provider banking session.

The parser handles only the fixed rebuilt local-hop request, not arbitrary
browser HTTP. Rejecting reordered fixed headers is expected for this narrow
contract, not a claim about generic HTTP. Neither this suite nor a callback200
creates a bank session or proves local-process authentication. The missing
relay, signer adapter, coordinator and Windows storage remain release gates.

Run both Python normal and -O discovery, and the complete Node suite on each
exact candidate. Earlier read-corpus integration showed that isolated Python
success is insufficient when a JSON schema is placed in another runner's
input directory. No existing Node inputs/runner or runtime logic are changed
by this integration.

The repository editor adds one final newline to the original JSON. All values
and vectors are unchanged. Original SHA256:
`f6eda001856ab11a24b31ac7b850498f48b876ede83498c749fec1234f22e6cb`.
Integrated SHA256:
`b8660cc68efc162dcdf030a4da145c8fb52ef3d8d7e893319e27518cd0a87d15`.
