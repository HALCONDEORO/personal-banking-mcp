import asyncio
import json
import unittest
import time
from unittest.mock import patch
import provider_pager
from dataclasses import replace
from provider_pager import FakeResponse, FetchStopped, HOST, Limits, fetch_simulated_transactions

ACCOUNT='00000000-0000-4000-8000-000000000001'

def movement(ref='a'):
    return {'transaction_amount':{'currency':'EUR','amount':'12.40'},
            'credit_debit_indicator':'DBIT','status':'BOOK','entry_reference':ref,
            'booking_date':'2026-01-03','remittance_information':['Synthetic private description']}

def response(rows=None, cursor=None):
    return FakeResponse(200,json.dumps({'transactions':rows or [],'continuation_key':cursor}).encode())

class PagerTests(unittest.IsolatedAsyncioTestCase):
    async def run_pages(self,pages,**kwargs):
        self.requests=[]
        async def transport(request):
            self.requests.append(request)
            return pages[len(self.requests)-1]
        return await fetch_simulated_transactions(ACCOUNT,frozenset([ACCOUNT]),'2026-01-01','2026-01-10',transport,**kwargs)
    async def test_empty_page_with_cursor_is_followed(self):
        result=await self.run_pages([response([], 'opaque'),response([movement()])])
        self.assertEqual(result['pages'],2)
        self.assertEqual(len(result['transactions']),1)
        self.assertTrue(result['provider_pagination_complete'])
        self.assertFalse(result['history_complete'])
        self.assertFalse(result['live'])
    async def test_requests_host_path_dates_fixed(self):
        await self.run_pages([response([], 'next'),response()])
        for request in self.requests:
            self.assertEqual(request.host,HOST)
            self.assertEqual(request.path,f'/accounts/{ACCOUNT}/transactions')
            self.assertEqual(dict(request.query)['date_from'],'2026-01-01')
            self.assertEqual(dict(request.query)['date_to'],'2026-01-10')
        self.assertEqual(dict(self.requests[1].query)['continuation_key'],'next')
    async def test_url_cursor_never_changes_destination(self):
        cursor='https://example.invalid/collect?secret=synthetic'
        await self.run_pages([response([],cursor),response()])
        self.assertEqual(self.requests[1].host,HOST)
        self.assertEqual(self.requests[1].path,f'/accounts/{ACCOUNT}/transactions')
        self.assertEqual(dict(self.requests[1].query)['continuation_key'],cursor)
    async def test_loop(self):
        with self.assertRaisesRegex(FetchStopped,'^cursor_loop$'):
            await self.run_pages([response([], 'same'),response([], 'same')])
        self.assertEqual(len(self.requests),2)
    async def test_page_budget(self):
        with self.assertRaisesRegex(FetchStopped,'^page_budget$'):
            await self.run_pages([response([], 'a')],limits=Limits(pages=1))
    async def test_row_budget(self):
        with self.assertRaisesRegex(FetchStopped,'^row_budget$'):
            await self.run_pages([response([movement('a'),movement('b')])],limits=Limits(rows=1))
    async def test_byte_budget(self):
        with self.assertRaisesRegex(FetchStopped,'^byte_budget$'):
            await self.run_pages([response()],limits=Limits(bytes_total=1))
    async def test_time_budget(self):
        async def slow(request):
            await asyncio.sleep(0.1)
            return response()
        with self.assertRaisesRegex(FetchStopped,'^time_budget$'):
            await fetch_simulated_transactions(ACCOUNT,frozenset([ACCOUNT]),'2026-01-01','2026-01-10',slow,limits=Limits(seconds=0.001))
    async def test_blocking_transport_cannot_return_late_success(self):
        async def slow(request):
            time.sleep(0.025)
            return response()
        with self.assertRaisesRegex(FetchStopped,'^time_budget$'):
            await fetch_simulated_transactions(ACCOUNT,frozenset([ACCOUNT]),'2026-01-01','2026-01-10',slow,limits=Limits(seconds=0.001))
    async def test_suppressed_cancellation_cannot_return_late_success(self):
        async def stubborn(request):
            try:
                await asyncio.sleep(0.050)
            except asyncio.CancelledError:
                return response()
        with self.assertRaisesRegex(FetchStopped,'^time_budget$'):
            await fetch_simulated_transactions(ACCOUNT,frozenset([ACCOUNT]),'2026-01-01','2026-01-10',stubborn,limits=Limits(seconds=0.001))
    async def test_slow_normalization_cannot_return_late_success(self):
        original=provider_pager.normalize_page
        def slow(payload):
            time.sleep(0.025)
            return original(payload)
        with patch.object(provider_pager,'normalize_page',slow):
            with self.assertRaisesRegex(FetchStopped,'^time_budget$'):
                await self.run_pages([response()],limits=Limits(seconds=0.010))
    async def test_status_errors_no_retry_or_private_payload(self):
        for status,code in [(401,'reconnect_required'),(403,'access_denied'),(422,'request_rejected'),(429,'rate_limited'),(500,'provider_unavailable'),(302,'unexpected_status')]:
            with self.subTest(status=status),self.assertRaisesRegex(FetchStopped,'^'+code+'$'):
                await self.run_pages([FakeResponse(status,b'PRIVATE-CANARY')])
            self.assertEqual(len(self.requests),1)
    async def test_duplicate_refs_no_silent_drop(self):
        with self.assertRaisesRegex(FetchStopped,'^duplicate_reference$'):
            await self.run_pages([response([movement()], 'next'),response([movement()])])
    async def test_no_reference_pending_preserved(self):
        row=movement(); row.pop('entry_reference'); row['status']='PDNG'
        out=await self.run_pages([response([row,row])])
        self.assertEqual(len(out['transactions']),2)
    async def test_invalid_json(self):
        for raw in [b'{broken',b'{"transactions":[],"transactions":[]}',b'{"transactions":NaN}',b'\xff',b'[]']:
            with self.subTest(raw=raw),self.assertRaisesRegex(FetchStopped,'^invalid_response$'):
                await self.run_pages([FakeResponse(200,raw)])
    async def test_invalid_record(self):
        row=movement(); row['transaction_amount']['amount']='Infinity'
        with self.assertRaisesRegex(FetchStopped,'^invalid_response$'):
            await self.run_pages([response([row])])
    async def test_account_rejected_before_transport(self):
        async def forbidden(request):
            self.fail('Transport must not run')
        for account in ['../secret','file:///secret','http://localhost','00000000-0000-4000-8000-000000000002']:
            with self.subTest(account=account),self.assertRaises(ValueError):
                await fetch_simulated_transactions(account,frozenset([ACCOUNT]),'2026-01-01','2026-01-10',forbidden)
    async def test_dates_rejected_before_transport(self):
        async def forbidden(request): self.fail('Transport must not run')
        for first,last in [('2026-02-30','2026-03-01'),('2026-01-10','2026-01-01'),('2024-01-01','2026-01-01')]:
            with self.assertRaises(ValueError):
                await fetch_simulated_transactions(ACCOUNT,frozenset([ACCOUNT]),first,last,forbidden)
    async def test_bad_local_limits(self):
        for limits in [Limits(pages=True),Limits(rows=0),Limits(bytes_total=1_000_001),Limits(seconds=float('nan')),Limits(seconds=-1),Limits(seconds=float('inf'))]:
            with self.subTest(limits=limits),self.assertRaises(ValueError):
                await self.run_pages([response()],limits=limits)
    async def test_transport_error_is_sanitized(self):
        async def broken(request): raise RuntimeError('PRIVATE-CANARY')
        with self.assertRaisesRegex(FetchStopped,'^transport_failure$'):
            await fetch_simulated_transactions(ACCOUNT,frozenset([ACCOUNT]),'2026-01-01','2026-01-10',broken)

if __name__=='__main__': unittest.main()
