import unittest
import json
import io
import gzip
import logging
from unittest.mock import patch
import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from provider_http import ReadOnlyHTTP, application_jwt, suppress_provider_diagnostics
from provider_pager import ReadRequest, FetchStopped, HOST

ACCOUNT='00000000-0000-4000-8000-000000000001'
SESSION='00000000-0000-4000-8000-000000000002'
TOKEN='synthetic.synthetic.synthetic'

class TestStream(httpx.AsyncByteStream):
    def __init__(self, body): self.body=body
    async def __aiter__(self):
        yield self.body

class HTTPTests(unittest.IsolatedAsyncioTestCase):
    def client(self, handler, **kwargs):
        self.requests=[]
        def track(request):
            self.requests.append(request)
            result=handler(request)
            if result.is_stream_consumed:
                return httpx.Response(result.status_code,headers=result.headers,stream=TestStream(result.content))
            return result
        return ReadOnlyHTTP(lambda:TOKEN,accounts=frozenset([ACCOUNT]),session=SESSION,
                            _test_transport=httpx.MockTransport(track),**kwargs)
    def request(self,path=None,query=()):
        return ReadRequest(HOST,path or f'/accounts/{ACCOUNT}/transactions',query)
    async def test_get_only_no_credentials_in_query(self):
        client=self.client(lambda r:httpx.Response(200,json={'transactions':[]}))
        out=await client(self.request(query=(('date_from','2026-01-01'),)))
        self.assertEqual(json.loads(out.body),{'transactions':[]})
        self.assertEqual(len(self.requests),1)
        request=self.requests[0]
        self.assertEqual(request.method,'GET')
        self.assertEqual(request.url.host,'api.enablebanking.com')
        self.assertNotIn(TOKEN,str(request.url))
        self.assertEqual(request.headers['Authorization'],'Bearer '+TOKEN)
    async def test_destination_denied_before_token_or_http(self):
        def forbidden(): self.fail('Must validate before credential access')
        client=ReadOnlyHTTP(forbidden,accounts=frozenset([ACCOUNT]),session=SESSION)
        for host,path in [('http://api.enablebanking.com',f'/accounts/{ACCOUNT}/balances'),('https://api.enablebanking.com.evil',f'/accounts/{ACCOUNT}/balances'),('https://127.0.0.1',f'/accounts/{ACCOUNT}/balances'),(HOST,'/payments'),(HOST,f'/accounts/{ACCOUNT}/balances?url=evil'),(HOST,'/sessions/00000000-0000-4000-8000-000000000003')]:
            with self.subTest(host=host,path=path),self.assertRaisesRegex(FetchStopped,'^operation_denied$'):
                await client(ReadRequest(host,path,()))
    async def test_account_scope(self):
        client=self.client(lambda r:self.fail('No HTTP'))
        with self.assertRaises(FetchStopped):
            await client(self.request('/accounts/00000000-0000-4000-8000-000000000003/balances'))
        self.assertFalse(self.requests)
    async def test_redirect_never_followed(self):
        client=self.client(lambda r:httpx.Response(302,headers={'location':'https://evil.invalid/private'}))
        out=await client(self.request())
        self.assertEqual(out.status,302); self.assertEqual(out.body,b'')
        self.assertEqual(len(self.requests),1)
    async def test_error_body_never_exposed(self):
        for status in [401,403,422,429,500]:
            client=self.client(lambda r:httpx.Response(status,content=b'PRIVATE-CANARY'))
            out=await client(self.request()); self.assertEqual(out.body,b'')
            self.assertEqual(len(self.requests),1)
    async def test_mime(self):
        client=self.client(lambda r:httpx.Response(200,content=b'<html>private</html>',headers={'content-type':'text/html'}))
        with self.assertRaisesRegex(FetchStopped,'^invalid_content_type$'): await client(self.request())
    async def test_byte_cap(self):
        client=self.client(lambda r:httpx.Response(200,content=b'X'*200,headers={'content-type':'application/json'}),max_bytes=100)
        with self.assertRaisesRegex(FetchStopped,'^byte_budget$'): await client(self.request())
    async def test_byte_cap_without_content_length(self):
        def reply(r):
            response=httpx.Response(200,content=b'X'*200,headers={'content-type':'application/json'})
            del response.headers['content-length']
            return response
        client=self.client(reply,max_bytes=100)
        with self.assertRaisesRegex(FetchStopped,'^byte_budget$'): await client(self.request())
    async def test_query_denylist_and_duplicates(self):
        client=self.client(lambda r:self.fail('No HTTP'))
        for query in [(('url','https://evil.invalid'),),(('date_from','bad'),),(('date_from','2026-01-01'),('date_from','2026-01-02')),(('continuation_key','a\nb'),),(('continuation_key','X'*2049),)]:
            with self.subTest(query=query),self.assertRaises(FetchStopped): await client(self.request(query=query))
        self.assertFalse(self.requests)
    async def test_balance_query_denied(self):
        client=self.client(lambda r:self.fail('No HTTP'))
        with self.assertRaises(FetchStopped): await client(self.request(f'/accounts/{ACCOUNT}/balances',(('continuation_key','x'),)))
    async def test_exceptions_sanitized(self):
        def broken(r): raise RuntimeError('PRIVATE-CANARY')
        client=self.client(broken)
        with self.assertRaisesRegex(FetchStopped,'^read_failed$'): await client(self.request())
    async def test_compressed_response_rejected_before_stream_read(self):
        class NeverRead(httpx.AsyncByteStream):
            async def __aiter__(self):
                raise AssertionError('Compressed stream was read')
                yield b''
        client=self.client(lambda r:httpx.Response(200,headers={'content-type':'application/json','content-encoding':'gzip'},stream=NeverRead()))
        with self.assertRaisesRegex(FetchStopped,'^content_encoding_denied$'):
            await client(self.request())
    async def test_sensitive_http_logs_suppressed(self):
        stream=io.StringIO(); handler=logging.StreamHandler(stream)
        names=['httpx','httpcore','httpcore.connection','httpcore.http11']
        previous=[]
        try:
            for name in names:
                logger=logging.getLogger(name)
                previous.append((logger,logger.level,logger.disabled,list(logger.filters)))
                logger.disabled=False; logger.setLevel(logging.DEBUG); logger.addHandler(handler)
            client=self.client(lambda r:httpx.Response(200,json={'transactions':[]}))
            await client(self.request(query=(('continuation_key','SYNTHETIC-CURSOR-CANARY'),)))
            for name in names:
                logging.getLogger(name).info('Synthetic private URL %s/accounts/%s?cursor=%s',HOST,ACCOUNT,'SYNTHETIC-CURSOR-CANARY')
            self.assertEqual(stream.getvalue(),'')
        finally:
            for logger,level,disabled,filters in previous:
                logger.removeHandler(handler); logger.setLevel(level); logger.disabled=disabled; logger.filters=filters
    async def test_future_child_logger_cannot_leak_to_root(self):
        stream=io.StringIO(); handler=logging.StreamHandler(stream)
        root=logging.getLogger(); previous=root.level
        root.addHandler(handler); root.setLevel(logging.DEBUG)
        child=None
        try:
            suppress_provider_diagnostics()
            child=logging.getLogger('httpcore.new_transport_logger_regression')
            child.disabled=False; child.setLevel(logging.INFO)
            child.info('SYNTHETIC-PRIVATE-CANARY')
            logging.getLogger('unrelated.application').warning('NON_SENSITIVE_EVENT')
            self.assertNotIn('SYNTHETIC-PRIVATE-CANARY',stream.getvalue())
            self.assertIn('NON_SENSITIVE_EVENT',stream.getvalue())
        finally:
            root.removeHandler(handler); root.setLevel(previous)
            if child: child.setLevel(logging.NOTSET)
    async def test_last_resort_handler_has_namespace_filter(self):
        stream=io.StringIO(); handler=logging.StreamHandler(stream)
        previous=logging.lastResort; logging.lastResort=handler
        try:
            suppress_provider_diagnostics()
            record=logging.LogRecord('httpcore.future',logging.ERROR,'',0,'PRIVATE-CANARY',(),None)
            handler.handle(record)
            self.assertEqual(stream.getvalue(),'')
        finally:
            logging.lastResort=previous
    async def test_import_no_network(self):
        # Construction does not create an HTTP client or request tokens.
        with patch('httpx.AsyncClient',side_effect=AssertionError('Unexpected client')):
            ReadOnlyHTTP(lambda:self.fail('Unexpected token'),accounts=frozenset([ACCOUNT]),session=SESSION)

class JWTTests(unittest.TestCase):
    def test_claims_algorithm_and_key_id(self):
        # Ephemeral test-only key remains in memory and is never written or printed.
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
        token=application_jwt(ACCOUNT,pem,now=1000)
        claims=jwt.decode(token,key.public_key(),algorithms=['RS256'],audience='api.enablebanking.com',issuer='enablebanking.com',options={'verify_exp':False})
        self.assertEqual(claims['iat'],1000); self.assertEqual(claims['exp'],1300)
        header=jwt.get_unverified_header(token)
        self.assertEqual(header['alg'],'RS256'); self.assertEqual(header['kid'],ACCOUNT)
    def test_invalid_configuration_sanitized(self):
        with self.assertRaisesRegex(ValueError,'^Application key configuration invalid$'):
            application_jwt(ACCOUNT,b'SYNTHETIC-PRIVATE-CANARY')

if __name__=='__main__': unittest.main()
