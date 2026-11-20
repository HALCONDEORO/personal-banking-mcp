# Session timezone validation, focused offline correction

Base: 532bf6971a9b62e01fb3cbb89e9cd71e02969740, after numeric JSON PR #30.

The session timestamp grammar previously accepted numeric timezone minutes 60 through 99. Python fromisoformat normalizes these instead of rejecting them, so an invalid provider expiry could become a future UTC time and permit an account read. The timestamp grammar now requires ASCII numeric timezone hours 00 through 23 and minutes 00 through 59 before conversion. Existing valid offsets, Z, fractional precision, strict date validity and UTC conversion rules remain.

The trusted-clock normalizer now converts unrepresentable UTC bounds into the same generic SessionRejected result as provider timestamp normalization. It previously leaked OverflowError for aware year-1/year-9999 boundary values; it never accepted those values. This is error consistency, not a claim that an expired date was accepted.

10 new test methods cover every invalid two-digit minute (60-99) with both signs and four hour ranges, every invalid hour (24-99), the creation repro, checked-session transport stopped before account read, valid extreme offsets, 20,000 deterministic valid UTC conversions, microsecond equality across offsets and UTC representability bounds. Baseline creation/read repro came from independent 4B audit; that original evidence remains separate from this candidate's regression suite.

377 Python tests pass normally and with -O. Node suites 9/55/58 pass with seed 377. Dependency check and diff whitespace check pass. No live provider, bank credentials, registration, Windows, money or host access. Local candidate only; review, PR-head verification and CI remain required before merge.
