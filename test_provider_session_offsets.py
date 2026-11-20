"""Offline synthetic regressions. No bank, network, credential or host access."""
import asyncio
import copy
from datetime import datetime,timedelta,timezone
import json
import random
import unittest
from provider_session import _time,_now,SessionRejected,PrivateSession,validate_created_session
from provider_checked_session import CheckedSessionRead,SessionReadStopped
from provider_pager import HOST,ReadRequest,FakeResponse

SID='11111111-1111-4111-8111-111111111111'
AID='22222222-2222-4222-8222-222222222222'
NOW=datetime(2026,11,20,10,tzinfo=timezone.utc)


def payload(until,checked=False):
    result={'psu_type':'personal','aspsp':{'name':'Synthetic bank','country':'IE'},'access':{'valid_until':until},
            'session_id':SID,'accounts':[AID] if checked else [{'uid':AID}]}
    if checked:result['status']='AUTHORIZED'
    return result


def create(until):
    return validate_created_session(payload(until),selected_bank='Synthetic bank',selected_country='IE',
                                    requested_until=NOW+timedelta(days=2),now=NOW)


class OffsetTests(unittest.TestCase):
    def test_all_invalid_offset_minutes_both_signs(self):
        for sign in ('+','-'):
            for minute in range(60,100):
                for hour in (0,1,22,23):
                    raw='2026-11-21T09:00:00'+sign+f'{hour:02d}:{minute:02d}'
                    with self.subTest(offset=raw),self.assertRaises(SessionRejected):_time(raw)
    def test_all_invalid_offset_hours(self):
        for sign in ('+','-'):
            for hour in range(24,100):
                raw='2026-11-21T09:00:00'+sign+f'{hour:02d}:00'
                with self.subTest(offset=raw),self.assertRaises(SessionRejected):_time(raw)
    def test_creation_rejects_normalized_offset_repro(self):
        for minute in range(60,100):
            raw=f'2026-11-20T09:00:00-00:{minute:02d}'
            with self.subTest(minute=minute),self.assertRaises(SessionRejected):create(raw)
    def test_valid_offsets_and_utc_results(self):
        rng=random.Random(20261120)
        for _ in range(20000):
            local=datetime(rng.randint(2,9998),rng.randint(1,12),rng.randint(1,28),rng.randrange(24),rng.randrange(60),rng.randrange(60),rng.randrange(1000000))
            dt=local.replace(tzinfo=timezone(timedelta(minutes=rng.randint(-1439,1439))))
            self.assertEqual(_time(dt.isoformat()),dt.astimezone(timezone.utc))
    def test_valid_extreme_offsets_and_fraction(self):
        for minutes in (-1439,-720,-1,0,1,720,1439):
            expiry=NOW+timedelta(hours=1,microseconds=1)
            raw=expiry.astimezone(timezone(timedelta(minutes=minutes))).isoformat()
            self.assertEqual(create(raw).summary(now=NOW)['valid_until'],expiry.isoformat())
        self.assertEqual(_time('2026-11-20T11:00:00Z'),NOW+timedelta(hours=1))
    def test_clock_utc_overflow_is_generic_session_rejection(self):
        for dt in (datetime.min.replace(tzinfo=timezone(timedelta(minutes=1))),datetime.max.replace(tzinfo=timezone(timedelta(minutes=-1)))):
            with self.subTest(clock=str(dt)),self.assertRaises(SessionRejected) as error:_now(dt)
            self.assertEqual(str(error.exception),'Session validation rejected')
    def test_unrepresentable_provider_utc_and_naive_clock_rejected(self):
        for raw in ('0001-01-01T00:00:00+00:01','9999-12-31T23:59:59.999999-00:01'):
            with self.assertRaises(SessionRejected):_time(raw)
        for dt in (datetime.now(),None,True):
            with self.assertRaises(SessionRejected):_now(dt)
    def test_expiry_equality_across_offset_extremes(self):
        for minutes in (-1439,-1,0,1,1439):
            for us in (-1,0,1):
                raw=(NOW+timedelta(microseconds=us)).astimezone(timezone(timedelta(minutes=minutes))).isoformat()
                if us>0:self.assertEqual(create(raw).summary(now=NOW)['account_count'],1)
                else:
                    with self.assertRaises(SessionRejected):create(raw)


class CheckedOffsetTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_offset_stops_before_account_effect(self):
        for minute in range(60,100):
            calls=[];value=payload(f'2026-11-20T09:00:00-00:{minute:02d}',checked=True)
            async def fake(req):
                calls.append(req.path)
                return FakeResponse(200,json.dumps(value).encode()) if req.path.startswith('/sessions/') else FakeResponse(200,b'{}')
            reader=CheckedSessionRead(session=PrivateSession(SID,(AID,),NOW+timedelta(hours=2)),bank='Synthetic bank',country='IE',transport=fake,now=lambda:NOW)
            with self.subTest(minute=minute),self.assertRaises(SessionReadStopped):await reader(ReadRequest(HOST,'/accounts/'+AID+'/balances',()))
            self.assertEqual(calls,['/sessions/'+SID])
    async def test_valid_extreme_offset_checks_then_reads(self):
        for minutes in (-1439,0,1439):
            calls=[];until=(NOW+timedelta(hours=1)).astimezone(timezone(timedelta(minutes=minutes))).isoformat()
            value=payload(until,checked=True)
            async def fake(req):
                calls.append(req.path)
                return FakeResponse(200,json.dumps(value).encode()) if req.path.startswith('/sessions/') else FakeResponse(200,b'{}')
            reader=CheckedSessionRead(session=PrivateSession(SID,(AID,),NOW+timedelta(hours=2)),bank='Synthetic bank',country='IE',transport=fake,now=lambda:NOW)
            result=await reader(ReadRequest(HOST,'/accounts/'+AID+'/balances',()))
            self.assertEqual(result.status,200);self.assertEqual(len(calls),2)

if __name__=='__main__':unittest.main()
