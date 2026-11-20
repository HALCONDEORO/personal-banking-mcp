"""Synthetic JSON-number regressions. No real provider, keys, session or bank."""
import json
from datetime import datetime,timezone,timedelta
import math
import traceback
import unittest
import httpx
from admin_http import AdminAISHTTP,AdminStopped
from provider_pager import (_strict_response_json,FetchStopped,FakeResponse,HOST,
                            ReadRequest,fetch_simulated_transactions)
from provider_checked_session import CheckedSessionRead,SessionReadStopped
from provider_session import PrivateSession

SID='11111111-1111-4111-8111-111111111111'
AID='22222222-2222-4222-8222-222222222222'
NOW=datetime(2026,11,20,tzinfo=timezone.utc)
BAD=('1e999','-1e999','1E+999','-9.9e999','NaN','Infinity','-Infinity')
GOOD=('1e3','-1e-3','1e308','-1e308','0.0','-0.0')


def with_extra(value,number):
    # Intentional raw JSON number, not json.dumps(inf) spelling. Invented data.
    prefix=json.dumps(value)[:-1]+(',' if value else '')
    return (prefix+'"extra":{"nested":[{"number":'+number+'}]}}').encode()


def session_payload():
    return {'status':'AUTHORIZED','psu_type':'personal',
            'aspsp':{'name':'Synthetic bank','country':'IE'},
            'access':{'valid_until':(NOW+timedelta(hours=1)).isoformat()},'accounts':[AID]}


class NumberParserTests(unittest.TestCase):
    def test_all_nonfinite_forms_rejected_nested(self):
        for number in BAD:
            with self.subTest(number=number),self.assertRaisesRegex(FetchStopped,'^invalid_response$'):
                _strict_response_json(with_extra({},number))

    def test_finite_exponents_preserved_in_non_money_extra(self):
        for number in GOOD:
            with self.subTest(number=number):
                result=_strict_response_json(with_extra({},number))
                self.assertTrue(math.isfinite(result['extra']['nested'][0]['number']))

    def test_nested_duplicate_and_money_string_semantics_retained(self):
        with self.assertRaises(FetchStopped):_strict_response_json(b'{"extra":{"x":1,"x":2}}')
        self.assertEqual(_strict_response_json(b'{"amount":"123456789012345.12345678"}')['amount'],
                         '123456789012345.12345678')


class NumberBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_pager_rejects_first_page_no_retry_or_second_call(self):
        for number in BAD:
            calls=[]
            async def fake(req):
                calls.append(req)
                return FakeResponse(200,with_extra({'transactions':[],'continuation_key':'synthetic-next'},number))
            with self.subTest(number=number),self.assertRaisesRegex(FetchStopped,'^invalid_response$'):
                await fetch_simulated_transactions(AID,frozenset([AID]),'2026-11-01','2026-11-20',fake)
            self.assertEqual(len(calls),1)

    async def test_pager_second_page_refusal_withholds_first_page(self):
        for number in BAD:
            calls=[]
            async def fake(req):
                calls.append(req)
                if len(calls)==1:return FakeResponse(200,b'{"transactions":[],"continuation_key":"synthetic-next"}')
                return FakeResponse(200,with_extra({'transactions':[]},number))
            with self.subTest(number=number),self.assertRaises(FetchStopped):
                await fetch_simulated_transactions(AID,frozenset([AID]),'2026-11-01','2026-11-20',fake)
            self.assertEqual(len(calls),2)

    async def test_session_check_refuses_before_account_read(self):
        for number in BAD:
            calls=[]
            async def fake(req):
                calls.append(req)
                return FakeResponse(200,with_extra(session_payload(),number))
            reader=CheckedSessionRead(session=PrivateSession(SID,(AID,),NOW+timedelta(hours=2)),
                                      bank='Synthetic bank',country='IE',transport=fake,now=lambda:NOW)
            with self.subTest(number=number),self.assertRaises(SessionReadStopped):
                await reader(ReadRequest(HOST,'/accounts/'+AID+'/balances',()))
            self.assertEqual([req.path for req in calls],['/sessions/'+SID])

    async def test_admin_exchange_refuses_private_reply_no_retry_or_leak(self):
        class Stream(httpx.AsyncByteStream):
            def __init__(self,raw):self.raw=raw
            async def __aiter__(self):yield self.raw
        for number in BAD:
            calls=[]
            raw=with_extra({'session_id':'SYNTHETIC-PRIVATE-CANARY'},number)
            def fake(req):
                calls.append(req)
                return httpx.Response(200,headers={'content-type':'application/json'},stream=Stream(raw))
            admin=AdminAISHTTP(lambda:'synthetic.synthetic.synthetic',_test_transport=httpx.MockTransport(fake))
            body={'code':'SYNTHETIC-CODE-CANARY'}
            try:await admin.exchange_code(body)
            except AdminStopped as error:
                rendered=''.join(traceback.format_exception(type(error),error,error.__traceback__))
                self.assertNotIn('SYNTHETIC-PRIVATE-CANARY',rendered)
                self.assertNotIn('SYNTHETIC-CODE-CANARY',rendered)
            else:self.fail('nonfinite admin response accepted')
            self.assertEqual(len(calls),1)

    async def test_finite_extra_numbers_do_not_change_existing_flows(self):
        class Stream(httpx.AsyncByteStream):
            def __init__(self,raw):self.raw=raw
            async def __aiter__(self):yield self.raw
        for number in GOOD:
            with self.subTest(number=number):
                async def pager(req):return FakeResponse(200,with_extra({'transactions':[]},number))
                page=await fetch_simulated_transactions(AID,frozenset([AID]),'2026-11-01','2026-11-20',pager)
                self.assertEqual(page['transactions'],[])
                self.assertFalse(page['live'])
                def fake(req):return httpx.Response(200,headers={'content-type':'application/json'},
                                                   stream=Stream(with_extra({'session_id':'SYNTHETIC-PRIVATE'},number)))
                admin=AdminAISHTTP(lambda:'synthetic.synthetic.synthetic',_test_transport=httpx.MockTransport(fake))
                reply=await admin.exchange_code({'code':'SYNTHETIC-CODE'})
                self.assertEqual(reply.take()['session_id'],'SYNTHETIC-PRIVATE')


if __name__=='__main__':unittest.main()
