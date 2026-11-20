# Admin authorization timestamp boundary

Base de790588c7203daa7e16e22208910e3e68947604. The admin POST /auth guard previously used fromisoformat directly and accepted malformed provider timestamp shapes, including offset minutes99, X separator and offset seconds. ConsentAttempt's normal builder creates a valid timestamp; no real authorization or expiry extension was observed in this audit.

Reuse the existing strict provider_session._time parser at the admin boundary. This aligns syntax and UTC representability without changing the authorization body or introducing a duration/current-time decision: the consent builder still owns that approved interval. Both start_authorization and the private _post guard reject malformed times before token retrieval or HTTP.

3 new test methods cover88 malformed timestamps through both entrypoints,800 parser-agreement combinations, valid offset extremes/Z/fractions unchanged and input immutability. 380 normal and optimized Python tests, Node9/55/58 seed380, pipcheck and diffcheck pass. Synthetic MockTransport only. No live provider, bank, credentials, Windows, registration, money or host activity.
