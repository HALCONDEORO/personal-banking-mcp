import asyncio
import base64
import json
import logging
import threading
import unittest
import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from provider_http import ReadOnlyHTTP, application_jwt
from provider_pager import ReadRequest, HOST
from signer_seam import FixedSigner, SignerSeamError, check_token_shape

APP = '00000000-0000-4000-8000-0000000000aa'
ACCOUNT = '00000000-0000-4000-8000-000000000001'
SESSION = '00000000-0000-4000-8000-000000000002'
NOW = 1_800_000_000
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
KEY = _KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                         serialization.NoEncryption())


class TestStream(httpx.AsyncByteStream):
    def __init__(self, body):
        self.body = body

    async def __aiter__(self):
        yield self.body


def b64(obj) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b'=').decode()


def forge(header=None, claims=None) -> str:
    h = {'alg': 'RS256', 'kid': APP, 'typ': 'JWT'} if header is None else header
    c = {'iss': 'enablebanking.com', 'aud': 'api.enablebanking.com',
         'iat': NOW, 'exp': NOW + 60} if claims is None else claims
    return b64(h) + '.' + b64(c) + '.c3ludGhldGlj'


def signer(backend):
    return FixedSigner(backend, APP, _clock=lambda: NOW)


class ShapeTests(unittest.TestCase):
    def test_accepts_fixed_shape_and_real_signed_token(self):
        self.assertEqual(signer(lambda: forge())(), forge())
        token = application_jwt(APP, KEY, now=NOW)
        self.assertEqual(signer(lambda: token)(), token)

    def test_rejects_every_deviation_generically(self):
        good = {'iss': 'enablebanking.com', 'aud': 'api.enablebanking.com', 'iat': NOW, 'exp': NOW + 60}
        bad = [
            forge(claims={**good, 'sub': 'x'}),
            forge(claims={k: v for k, v in good.items() if k != 'iat'}),
            forge(claims={**good, 'iss': 'evil.example'}),
            forge(claims={**good, 'aud': 'evil.example'}),
            forge(claims={**good, 'exp': NOW + 301}),
            forge(claims={**good, 'exp': NOW}),
            forge(claims={**good, 'exp': NOW - 1, 'iat': NOW - 60}),
            forge(claims={**good, 'iat': NOW + 31, 'exp': NOW + 90}),
            forge(claims={**good, 'iat': True, 'exp': NOW + 60}),
            forge(claims={**good, 'iat': float(NOW)}),
            forge(header={'alg': 'none', 'kid': APP}),
            forge(header={'alg': 'HS256', 'kid': APP}),
            forge(header={'alg': 'RS256', 'kid': 'other'}),
            forge(header={'alg': 'RS256', 'kid': APP, 'jku': 'https://x.example'}),
            'not-a-token', '', None, 12, b'a.b.c', 'a.b', 'a.b.c.d',
            'A' * 16_400 + '.b.c',
            forge().replace('.', '=.', 1),
        ]
        for token in bad:
            with self.subTest(token=str(token)[:20]):
                with self.assertRaises(SignerSeamError) as caught:
                    signer(lambda t=token: t)()
                self.assertEqual(str(caught.exception), 'Signer unavailable')
                self.assertIsNone(caught.exception.__cause__)

    def test_duplicate_keys_rejected_in_header_and_claims(self):
        def raw(head, body):
            enc = lambda x: base64.urlsafe_b64encode(x.encode()).rstrip(b'=').decode()
            return enc(head) + '.' + enc(body) + '.c2ln'
        h = '{"alg":"RS256","kid":"%s"}' % APP
        c = '{"iss":"enablebanking.com","aud":"api.enablebanking.com","iat":%d,"exp":%d}' % (NOW, NOW + 60)
        self.assertEqual(signer(lambda: raw(h, c))(), raw(h, c))  # control: accepted
        cases = {
            'alg none then RS256': ('{"alg":"none","alg":"RS256","kid":"%s"}' % APP, c),
            'alg identical': ('{"alg":"RS256","alg":"RS256","kid":"%s"}' % APP, c),
            'kid identical': ('{"alg":"RS256","kid":"%s","kid":"%s"}' % (APP, APP), c),
            'iss evil then real': (h, c.replace('{', '{"iss":"evil.example",', 1)),
            'iss identical': (h, c.replace('{', '{"iss":"enablebanking.com",', 1)),
            'exp identical': (h, c[:-1] + ',"exp":%d}' % (NOW + 60)),
            'escaped duplicate': (h, c[:-1] + ',"\\u0069ss":"evil.example"}'),
            'typ identical': ('{"alg":"RS256","kid":"%s","typ":"JWT","typ":"JWT"}' % APP, c),
        }
        for name, (head, body) in cases.items():
            with self.subTest(name):
                with self.assertRaises(SignerSeamError):
                    signer(lambda t=raw(head, body): t)()

    def test_nonfinite_json_constants_rejected(self):
        raw = '{"iss":"enablebanking.com","aud":"api.enablebanking.com","iat":1,"exp":NaN}'
        tok = b64({'alg': 'RS256', 'kid': APP}) + '.' + base64.urlsafe_b64encode(raw.encode()).rstrip(b'=').decode() + '.c2ln'
        with self.assertRaises(ValueError):
            check_token_shape(tok, APP, now=NOW)

    def test_bad_construction(self):
        for backend, app in [(None, APP), (lambda: '', 'not-a-uuid'), (lambda: '', APP.upper())]:
            with self.assertRaises(SignerSeamError):
                FixedSigner(backend, app)


class LeakAndStateTests(unittest.TestCase):
    def test_backend_error_text_never_surfaces(self):
        secret = 'PRIVATE-KEY-MATERIAL-SYNTHETIC'
        def boom():
            raise RuntimeError(secret)
        with self.assertRaises(SignerSeamError) as caught:
            signer(boom)()
        text = repr(caught.exception) + str(caught.exception) + repr(caught.exception.__context__)
        self.assertNotIn(secret, text)
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)

    def test_repr_and_pickle_do_not_expose_backend_or_token(self):
        token = forge()
        s = signer(lambda: token)
        s()
        self.assertEqual(repr(s), 'FixedSigner()')
        self.assertNotIn(token, repr(s) + str(s))
        import pickle
        with self.assertRaises(TypeError):
            pickle.dumps(s)
        with self.assertRaises(AttributeError):
            s.extra = 1

    def test_no_logging_output(self):
        with self.assertNoLogs(level=logging.DEBUG):
            signer(lambda: forge())()
            with self.assertRaises(SignerSeamError):
                signer(lambda: 'x')()

    def test_no_retry_and_no_cache(self):
        calls = []
        def backend():
            calls.append(1)
            raise RuntimeError
        s = signer(backend)
        with self.assertRaises(SignerSeamError):
            s()
        self.assertEqual(len(calls), 1)
        ok = []
        s2 = signer(lambda: ok.append(1) or forge())
        s2(); s2()
        self.assertEqual(len(ok), 2)

    def test_concurrent_call_fails_instead_of_queueing(self):
        entered, release = threading.Event(), threading.Event()
        def slow():
            entered.set()
            release.wait(2)
            return forge()
        s = signer(slow)
        out = []
        t = threading.Thread(target=lambda: out.append(s()))
        t.start()
        self.assertTrue(entered.wait(2))
        with self.assertRaises(SignerSeamError):
            s()
        release.set(); t.join(2)
        self.assertEqual(out, [forge()])
        self.assertEqual(s(), forge())  # lock released

    def test_backend_takes_no_arguments(self):
        seen = []
        signer(lambda *a, **k: seen.append((a, k)) or forge())()
        self.assertEqual(seen, [((), {})])

    def test_module_has_no_io_surface(self):
        import signer_seam, inspect
        src = inspect.getsource(signer_seam)
        for word in ('subprocess', 'socket', 'import os', 'sys.stdout', 'print(', 'open(', 'http'):
            self.assertNotIn(word, src.replace('api.enablebanking.com', ''), word)


class TransportJoinTests(unittest.IsolatedAsyncioTestCase):
    async def test_readonlyhttp_uses_checked_token_and_mock_transport_only(self):
        seen = []
        def handler(request):
            seen.append(request.headers['authorization'])
            return httpx.Response(200, headers={'content-type': 'application/json'}, stream=TestStream(b'{}'))
        token = application_jwt(APP, KEY)
        http = ReadOnlyHTTP(FixedSigner(lambda: token, APP), accounts=frozenset({ACCOUNT}),
                            session=SESSION, _test_transport=httpx.MockTransport(handler))
        response = await http(ReadRequest(HOST, f'/accounts/{ACCOUNT}/balances', ()))
        self.assertEqual(response.status, 200)
        self.assertEqual(seen, ['Bearer ' + token])

    async def test_bad_token_makes_no_request(self):
        seen = []
        http = ReadOnlyHTTP(FixedSigner(lambda: forge(claims={'x': 1}), APP, _clock=lambda: NOW),
                            accounts=frozenset({ACCOUNT}), session=SESSION,
                            _test_transport=httpx.MockTransport(lambda r: seen.append(r)))
        with self.assertRaises(Exception) as caught:
            await http(ReadRequest(HOST, f'/accounts/{ACCOUNT}/balances', ()))
        self.assertEqual(seen, [])
        self.assertNotIn('Bearer', repr(caught.exception))


if __name__ == '__main__':
    unittest.main()
