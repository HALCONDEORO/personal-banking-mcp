import time
import unittest
import httpx
from provider_http import ReadOnlyHTTP, application_jwt
from provider_pager import ReadRequest, FetchStopped, HOST
from signer_seam import FixedSigner, SignerSeamError
from test_signer_seam import APP, ACCOUNT, SESSION, KEY, TestStream


class SlowBackendTests(unittest.IsolatedAsyncioTestCase):
    def http(self, backend, seen, **kw):
        def handler(request):
            seen.append(request)
            return httpx.Response(200, headers={'content-type': 'application/json'}, stream=TestStream(b'{}'))
        return ReadOnlyHTTP(FixedSigner(backend, APP), accounts=frozenset({ACCOUNT}), session=SESSION,
                            _test_transport=httpx.MockTransport(handler), **kw)

    def request(self):
        return ReadRequest(HOST, f'/accounts/{ACCOUNT}/balances', ())

    async def test_blocking_backend_past_budget_is_not_accepted_and_sends_nothing(self):
        # A synchronous backend blocks the event loop; the transport must still
        # refuse to continue once its deadline has passed.
        seen = []
        def slow():
            time.sleep(0.3)
            return application_jwt(APP, KEY)
        http = self.http(slow, seen, total_seconds=0.1)
        with self.assertRaises(FetchStopped) as caught:
            await http(self.request())
        self.assertEqual(str(caught.exception), 'time_budget')
        self.assertEqual(seen, [])

    async def test_backend_failure_means_no_request_and_no_retry(self):
        seen, calls = [], []
        def broken():
            calls.append(1)
            raise RuntimeError('SYNTHETIC-SECRET')
        http = self.http(broken, seen)
        with self.assertRaises(FetchStopped) as caught:
            await http(self.request())
        self.assertEqual(seen, [])
        self.assertEqual(len(calls), 1)
        self.assertNotIn('SYNTHETIC-SECRET', repr(caught.exception) + str(caught.exception))

    async def test_fast_backend_still_works_after_a_slow_failure(self):
        seen = []
        state = {'slow': True}
        def backend():
            if state['slow']:
                state['slow'] = False
                time.sleep(0.3)
            return application_jwt(APP, KEY)
        http = self.http(backend, seen, total_seconds=0.1)
        with self.assertRaises(FetchStopped):
            await http(self.request())
        out = await http(self.request())
        self.assertEqual(out.status, 200)
        self.assertEqual(len(seen), 1)


if __name__ == '__main__':
    unittest.main()
