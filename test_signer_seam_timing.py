import time
import types
import unittest
from unittest.mock import patch
import httpx
import provider_http
from provider_http import ReadOnlyHTTP, application_jwt
from provider_pager import ReadRequest, FetchStopped, HOST
from signer_seam import FixedSigner
from test_signer_seam import APP, ACCOUNT, SESSION, KEY, TestStream


class FakeClock:
    """Explicit monotonic clock. Nothing here sleeps or depends on real speed."""
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class SignerBackendTimingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock = FakeClock()
        # Replace only the transport's `time` name, not the global time module, so
        # asyncio keeps its real clock. total_seconds stays at the 5 s default.
        fake_time = types.SimpleNamespace(monotonic=self.clock.monotonic, time=time.time)
        patcher = patch.object(provider_http, 'time', fake_time)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.seen = []

    def http(self, backend):
        def handler(request):
            self.seen.append(request)
            return httpx.Response(200, headers={'content-type': 'application/json'}, stream=TestStream(b'{}'))
        return ReadOnlyHTTP(FixedSigner(backend, APP), accounts=frozenset({ACCOUNT}), session=SESSION,
                            _test_transport=httpx.MockTransport(handler))

    def request(self):
        return ReadRequest(HOST, f'/accounts/{ACCOUNT}/balances', ())

    async def test_backend_that_overruns_budget_is_not_accepted_and_sends_nothing(self):
        def slow():
            self.clock.advance(10)  # well past the 5 s budget, no real waiting
            return application_jwt(APP, KEY)
        with self.assertRaises(FetchStopped) as caught:
            await self.http(slow)(self.request())
        self.assertEqual(str(caught.exception), 'time_budget')
        self.assertEqual(self.seen, [])

    async def test_backend_failure_means_no_request_and_no_retry(self):
        calls = []
        def broken():
            calls.append(1)
            raise RuntimeError('SYNTHETIC-SECRET')
        with self.assertRaises(FetchStopped) as caught:
            await self.http(broken)(self.request())
        self.assertEqual(self.seen, [])
        self.assertEqual(len(calls), 1)
        self.assertNotIn('SYNTHETIC-SECRET', repr(caught.exception) + str(caught.exception))

    async def test_next_call_works_after_an_overrun(self):
        state = {'slow': True}
        def backend():
            if state['slow']:
                state['slow'] = False
                self.clock.advance(10)
            return application_jwt(APP, KEY)
        http = self.http(backend)
        with self.assertRaises(FetchStopped):
            await http(self.request())
        out = await http(self.request())  # clock no longer advances: deterministic
        self.assertEqual(out.status, 200)
        self.assertEqual(len(self.seen), 1)


if __name__ == '__main__':
    unittest.main()
