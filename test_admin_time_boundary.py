"""Synthetic-only admin-boundary timestamps. No provider or credentials."""
import copy
import json
import unittest
import httpx
from admin_http import AdminAISHTTP,AdminStopped,_auth_body
from provider_session import _time

BODY={'access':{'valid_until':'2026-11-21T10:00:00Z'},'aspsp':{'name':'Synthetic bank','country':'IE'},
      'state':'x'*43,'redirect_url':'https://localhost:8765/callback','psu_type':'personal'}
URL='https://auth.enablebanking.com/ais/start?sessionid=11111111-1111-4111-8111-111111111111'


def body(raw):
    result=copy.deepcopy(BODY);result['access']['valid_until']=raw;return result


class AdminTimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_malformed_timestamps_deny_before_token_or_http(self):
        client=AdminAISHTTP(lambda:self.fail('token accessed'),_test_transport=httpx.MockTransport(lambda req:self.fail('HTTP accessed')))
        bad=['2026-11-20T09:00:00-00:99','2026-11-20X09:00:00+00:00','2026-11-20T09:00:00+00:00:01',
             '2026-11-20 09:00:00+00:00','2026-11-20T09:00:00.1234567Z','2026-11-20T09:00:00+24:00',
             '0001-01-01T00:00:00+00:01','9999-12-31T23:59:59.999999-00:01']
        bad += [f'2026-11-20T09:00:00{sign}00:{minute:02d}' for sign in ('+','-') for minute in range(60,100)]
        for raw in bad:
            for entrypoint in ('start','post'):
                with self.subTest(raw=raw,entrypoint=entrypoint),self.assertRaises(AdminStopped):
                    if entrypoint=='start':await client.start_authorization(body(raw))
                    else:await client._post('/auth',body(raw))
    async def test_valid_timestamps_preserved_no_implicit_extension(self):
        seen=[]
        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):yield json.dumps({'url':URL}).encode()
        def handle(req):
            seen.append(json.loads(req.content));return httpx.Response(200,headers={'content-type':'application/json'},stream=Stream())
        client=AdminAISHTTP(lambda:'synthetic.synthetic.synthetic',_test_transport=httpx.MockTransport(handle))
        for raw in ('2026-11-21T10:00:00Z','2026-11-21T10:00:00.123456+23:59','2026-11-21T10:00:00-23:59','2026-11-21T10:00:00+00:00'):
            before=body(raw);snapshot=copy.deepcopy(before)
            reply=await client.start_authorization(before)
            self.assertEqual(reply.take(),{'url':URL});self.assertEqual(seen[-1]['access']['valid_until'],raw);self.assertEqual(before,snapshot)
    async def test_admin_and_session_grammar_agree(self):
        for sign in ('+','-'):
            for hour in range(100):
                for minute in (0,59,60,99):
                    raw=f'2026-11-21T10:00:00{sign}{hour:02d}:{minute:02d}'
                    try:_time(raw);expected=True
                    except ValueError:expected=False
                    try:_auth_body(body(raw));actual=True
                    except AdminStopped:actual=False
                    self.assertEqual(actual,expected)

if __name__=='__main__':unittest.main()
