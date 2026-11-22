import asyncio
import copy
from datetime import datetime, timezone, timedelta
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from async_boundary import _await_owned as real_await_owned
from provider_session import PrivateSession
from provider_checked_session import CheckedSessionRead, SessionReadStopped
from provider_pager import HOST, ReadRequest, FakeResponse

SID='11111111-1111-4111-8111-111111111111'
AID='22222222-2222-4222-8222-222222222222'
OTHER='33333333-3333-4333-8333-333333333333'
NOW=datetime(2026,11,20,tzinfo=timezone.utc)

def payload():
    return {'status':'AUTHORIZED','psu_type':'personal','aspsp':{'name':'Synthetic bank','country':'IE'},
            'access':{'valid_until':(NOW+timedelta(hours=1)).isoformat()},'accounts':[AID]}

def request(path=None,query=()):
    return ReadRequest(HOST,path or '/accounts/'+AID+'/balances',query)

class CheckedTests(unittest.IsolatedAsyncioTestCase):
    def fixture(self, *, value=None, transport=None, seconds=1):
        self.calls=[];self.now=NOW;self.value=payload() if value is None else value
        async def fake(req):
            self.calls.append(req)
            return FakeResponse(200,json.dumps(self.value).encode()) if req.path.startswith('/sessions/') else FakeResponse(200,b'{"balances":[]}')
        self.reader=CheckedSessionRead(session=PrivateSession(SID,(AID,),NOW+timedelta(hours=2)),bank='Synthetic bank',country='IE',transport=transport or fake,now=lambda:self.now,seconds=seconds)
        return self.reader
    async def test_check_immediately_before_each_read(self):
        r=self.fixture();await r(request());await r(request())
        self.assertEqual([x.path for x in self.calls],['/sessions/'+SID,'/accounts/'+AID+'/balances']*2)
        self.assertNotIn(AID,repr(r));self.assertNotIn(SID,repr(r))
    async def test_no_cache_after_revocation(self):
        r=self.fixture();await r(request());self.value['status']='REVOKED'
        with self.assertRaises(SessionReadStopped):await r(request())
        self.assertEqual(len(self.calls),3)
    async def test_non_authorized_statuses_deny_account_call(self):
        for status in ['CANCELLED','CLOSED','EXPIRED','INVALID','PENDING_AUTHORIZATION','RETURNED_FROM_BANK','authorized',None,True]:
            data=payload();data['status']=status;r=self.fixture(value=data)
            with self.subTest(status=status),self.assertRaises(SessionReadStopped):await r(request())
            self.assertEqual(len(self.calls),1)
    async def test_expired_local_session_denies_before_transport(self):
        r=self.fixture();self.now=NOW+timedelta(hours=3)
        with self.assertRaises(SessionReadStopped):await r(request())
        self.assertEqual(self.calls,[])
    async def test_bank_country_personal_scope_closed_expiry_and_accounts(self):
        mutations=[lambda p:p.update(psu_type='business'),lambda p:p.update(closed=NOW.isoformat()),lambda p:p['aspsp'].update(country='ES'),lambda p:p['aspsp'].update(name='Other'),lambda p:p['access'].update(valid_until=NOW.isoformat()),lambda p:p.update(accounts=[OTHER]),lambda p:p.update(accounts=[AID,AID]),lambda p:p.update(accounts=['private-invalid-id'])]
        for mutate in mutations:
            p=payload();mutate(p);r=self.fixture(value=p)
            with self.assertRaises(SessionReadStopped):await r(request())
            self.assertEqual(len(self.calls),1)
    async def test_extra_provider_accounts_not_adopted(self):
        p=payload();p['accounts'].append(OTHER);r=self.fixture(value=p);await r(request())
        with self.assertRaises(SessionReadStopped):await r(request('/accounts/'+OTHER+'/details'))
        self.assertEqual(len(self.calls),2)
    async def test_arbitrary_host_path_and_query_denied_before_session_read(self):
        for req in [ReadRequest('https://example.invalid',request().path,()),request('/sessions/'+SID),request('/accounts/'+AID+'/payments'),request(query=(('bad','x'),)),request(query=(('date_from','2026-02-30'),)),request(query=(('strategy','longest'),))]:
            r=self.fixture()
            with self.assertRaises(SessionReadStopped):await r(req)
            self.assertEqual(self.calls,[])
    async def test_session_bad_http_duplicate_json_oversize_no_second_call(self):
        for response in [FakeResponse(401,b'private'),FakeResponse(429,b'private'),FakeResponse(302,b'private'),FakeResponse(200,b'{"status":"AUTHORIZED","status":"AUTHORIZED"}'),FakeResponse(200,b'x'*65537),FakeResponse(True,b'{}')]:
            calls=[]
            async def fake(req):calls.append(req);return response
            r=self.fixture(transport=fake)
            with self.assertRaises(SessionReadStopped):await r(request())
            self.assertEqual(len(calls),1)
    async def test_expiry_during_session_check_prevents_account_read(self):
        calls=[]
        async def fake(req):
            calls.append(req);self.now=NOW+timedelta(hours=3);return FakeResponse(200,json.dumps(payload()).encode())
        r=self.fixture(transport=fake)
        with self.assertRaises(SessionReadStopped):await r(request())
        self.assertEqual(len(calls),1)
    async def test_suppressed_cancellation_cannot_start_second_effect_after_deadline(self):
        # Control ONLY this module's deadline clock, never the event loop clock.
        ticks=[100.0];calls=[];entered=asyncio.Event();suppressed=asyncio.Event()
        clocked_asyncio=SimpleNamespace(
            Lock=asyncio.Lock,CancelledError=asyncio.CancelledError,
            get_running_loop=lambda:SimpleNamespace(time=lambda:ticks[0]))
        async def fake(req):
            calls.append(req);entered.set()
            try:await asyncio.Future()
            except asyncio.CancelledError:suppressed.set()
            return FakeResponse(200,json.dumps(payload()).encode())
        boundaries=[]
        async def schedule_owned(coro,seconds):
            boundaries.append(seconds)
            if len(boundaries)==1:
                # Real owned outer task; 5s is a safety watchdog, not the test clock.
                return await real_await_owned(coro,5)
            if len(boundaries)==2:
                task=asyncio.create_task(coro)
                try:
                    await asyncio.wait_for(entered.wait(),2)
                    # First effect has started. Expire the logical 101.0 deadline,
                    # then force the REAL owned-await timeout/cancellation path.
                    ticks[0]=102.0
                    return await real_await_owned(task,0)
                finally:
                    if not task.done():task.cancel()
                    await asyncio.gather(task,return_exceptions=True)
            return await real_await_owned(coro,5)
        with patch('provider_checked_session.asyncio',clocked_asyncio),patch('provider_checked_session._await_owned',schedule_owned):
            r=self.fixture(transport=fake,seconds=1)
            with self.assertRaises(SessionReadStopped):await r(request())
        self.assertTrue(entered.is_set());self.assertTrue(suppressed.is_set())
        self.assertEqual([call.path for call in calls],['/sessions/'+SID])
        self.assertEqual(len(boundaries),2)
        self.assertFalse(r._lock.locked())
    async def test_deadline_expired_before_workflow_has_zero_effects(self):
        ticks=[100.0];calls=[];entered=asyncio.Event();boundaries=[]
        clocked_asyncio=SimpleNamespace(
            Lock=asyncio.Lock,CancelledError=asyncio.CancelledError,
            get_running_loop=lambda:SimpleNamespace(time=lambda:ticks[0]))
        async def fake(req):
            calls.append(req);entered.set()
            return FakeResponse(200,json.dumps(payload()).encode())
        async def expire_before_start(coro,seconds):
            boundaries.append(seconds)
            ticks[0]=102.0
            return await real_await_owned(coro,5)
        with patch('provider_checked_session.asyncio',clocked_asyncio),patch('provider_checked_session._await_owned',expire_before_start):
            r=self.fixture(transport=fake,seconds=1)
            with self.assertRaises(SessionReadStopped):await r(request())
        self.assertFalse(entered.is_set());self.assertEqual(calls,[])
        self.assertEqual(len(boundaries),1)
        self.assertFalse(r._lock.locked())
    async def test_cancellation_propagates_no_retry(self):
        entered=asyncio.Event();calls=[]
        async def fake(req):calls.append(req);entered.set();await asyncio.sleep(5)
        r=self.fixture(transport=fake);task=asyncio.create_task(r(request()));await entered.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(len(calls),1)
    async def test_no_private_error_body_or_context(self):
        async def fake(req):raise ValueError('synthetic-private-id')
        r=self.fixture(transport=fake)
        with self.assertRaises(SessionReadStopped) as caught:await r(request())
        self.assertNotIn('synthetic-private',str(caught.exception));self.assertIsNone(caught.exception.__context__)
    async def test_parallel_workflows_serialized_as_pairs(self):
        r=self.fixture();await asyncio.gather(r(request()),r(request()))
        self.assertEqual([x.path.startswith('/sessions/') for x in self.calls],[True,False,True,False])
    async def test_provider_expiry_between_check_and_account_effect(self):
        data=payload();data['access']['valid_until']=(NOW+timedelta(seconds=1)).isoformat()
        r=self.fixture(value=data);ticks=iter([NOW,NOW,NOW,NOW,NOW+timedelta(seconds=2)])
        r._now=lambda:next(ticks)
        with self.assertRaises(SessionReadStopped):await r(request())
        self.assertEqual(len(self.calls),1)
    async def test_provider_expiry_during_account_effect_withholds_result(self):
        calls=[];data=payload();data['access']['valid_until']=(NOW+timedelta(seconds=1)).isoformat()
        async def fake(req):
            calls.append(req)
            if req.path.startswith('/sessions/'):return FakeResponse(200,json.dumps(data).encode())
            self.now=NOW+timedelta(seconds=2);return FakeResponse(200,b'{"balances":[]}')
        r=self.fixture(transport=fake)
        with self.assertRaises(SessionReadStopped):await r(request())
        self.assertEqual(len(calls),2)
    async def test_real_pager_revocation_between_pages_yields_no_partial_result(self):
        from provider_pager import fetch_simulated_transactions, FetchStopped
        calls=[];checks=0
        async def fake(req):
            nonlocal checks
            calls.append(req)
            if req.path.startswith('/sessions/'):
                checks+=1;data=payload()
                if checks==2:data['status']='REVOKED'
                return FakeResponse(200,json.dumps(data).encode())
            return FakeResponse(200,b'{"transactions":[],"continuation_key":"synthetic-next"}')
        r=self.fixture(transport=fake)
        with self.assertRaises(FetchStopped):
            await fetch_simulated_transactions(AID,frozenset([AID]),'2026-11-01','2026-11-20',r)
        self.assertEqual([x.path for x in calls],['/sessions/'+SID,'/accounts/'+AID+'/transactions','/sessions/'+SID])
    async def test_no_caller_input_mutation(self):
        p=payload();before=copy.deepcopy(p);r=self.fixture(value=p);await r(request());self.assertEqual(p,before)

if __name__=='__main__':unittest.main()
