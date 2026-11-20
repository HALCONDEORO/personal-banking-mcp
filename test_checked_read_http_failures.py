# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Failure boundaries across the pager/session/HTTP stack, mock HTTP only."""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import unittest

import httpx
from provider_checked_session import CheckedSessionRead
from provider_http import ReadOnlyHTTP
from provider_pager import FetchStopped, fetch_simulated_transactions
from provider_session import PrivateSession
SID = '11111111-1111-4111-8111-111111111111'
AID = '22222222-2222-4222-8222-222222222222'
NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)


class CheckedHTTPFailureTests(unittest.IsolatedAsyncioTestCase):
    def build(self, mode='ok'):
        self.calls = []
        self.tokens = 0
        self.pages = 0
        self.now = NOW
        self.first_page_sent = False
        self.blocked = asyncio.Event()
        self.cancelled = asyncio.Event()

        async def handler(request):
            self.calls.append(request)
            if request.url.path == '/sessions/' + SID:
                payload = {
                    'status': 'AUTHORIZED', 'psu_type': 'personal',
                    'aspsp': {'name': 'Synthetic bank', 'country': 'IE'},
                    'access': {'valid_until': (NOW + timedelta(hours=1)).isoformat()},
                    'accounts': [AID],
                }
            else:
                self.pages += 1
                if self.pages == 1:
                    self.first_page_sent = True
                    payload = {'transactions': [{
                        'transaction_amount': {'amount': '12.34', 'currency': 'EUR'},
                        'credit_debit_indicator': 'DBIT', 'status': 'BOOK',
                        'transaction_date': '2026-11-01',
                        'remittance_information': ['SYNTHETIC-FIRST-PAGE'],
                    }], 'continuation_key': 'synthetic-next'}
                else:
                    if mode == 'cancel':
                        self.blocked.set()
                        try:
                            await asyncio.Event().wait()
                        except asyncio.CancelledError:
                            self.cancelled.set()
                            raise
                    if mode == 'redirect':
                        return httpx.Response(302, headers={
                            'location': 'https://synthetic.invalid/not-followed'},
                            stream=httpx.ByteStream(b'SYNTHETIC-PRIVATE-ERROR'))
                    if mode == 'throttle':
                        return httpx.Response(429, stream=httpx.ByteStream(b'SYNTHETIC-PRIVATE-ERROR'))
                    if mode == 'malformed':
                        return httpx.Response(200, headers={'content-type': 'application/json'},
                                              stream=httpx.ByteStream(b'{SYNTHETIC-PRIVATE-ERROR'))
                    if mode == 'duplicate':
                        return httpx.Response(200, headers={'content-type': 'application/json'},
                            stream=httpx.ByteStream(b'{"transactions":[],"transactions":[],"continuation_key":null}'))
                    if mode == 'provider_expiry':
                        self.now = NOW + timedelta(hours=1)
                    if mode == 'local_expiry':
                        self.now = NOW + timedelta(hours=2)
                    payload = {'transactions': [], 'continuation_key': None}
            return httpx.Response(200, headers={'content-type': 'application/json'},
                                  stream=httpx.ByteStream(json.dumps(payload).encode()))

        def token():
            self.tokens += 1
            return 'synthetic.synthetic.synthetic'

        http = ReadOnlyHTTP(token, accounts=frozenset([AID]), session=SID,
                            _test_transport=httpx.MockTransport(handler))
        return CheckedSessionRead(
            session=PrivateSession(SID, (AID,), NOW + timedelta(hours=2)),
            bank='Synthetic bank', country='IE', transport=http, now=lambda: self.now)

    async def read(self, reader):
        return await fetch_simulated_transactions(
            AID, frozenset([AID]), '2026-11-01', '2026-11-20', reader)

    def assert_two_pages_only(self):
        self.assertTrue(self.first_page_sent)
        self.assertEqual((self.pages, self.tokens), (2, 4))
        self.assertEqual([request.url.path for request in self.calls],
                         ['/sessions/' + SID, '/accounts/' + AID + '/transactions'] * 2)
        self.assertTrue(all(request.method == 'GET' for request in self.calls))
        self.assertTrue(all(request.url.host == 'api.enablebanking.com' for request in self.calls))
        self.assertEqual(self.calls[-1].url.params['continuation_key'], 'synthetic-next')

    async def expect_stopped(self, mode, code):
        with self.assertRaises(FetchStopped) as error:
            await self.read(self.build(mode))
        self.assertEqual(error.exception.args, (code,))
        self.assertNotIn('SYNTHETIC-FIRST-PAGE', str(error.exception))
        self.assertNotIn('SYNTHETIC-PRIVATE-ERROR', str(error.exception))
        self.assertIsNone(error.exception.__cause__)
        self.assertTrue(error.exception.__context__ is None or error.exception.__suppress_context__)
        self.assert_two_pages_only()

    async def test_positive_first_row_reaches_complete_mock_result(self):
        result = await self.read(self.build())
        self.assert_two_pages_only()
        self.assertEqual(result['transactions'][0]['description'], 'SYNTHETIC-FIRST-PAGE')
        self.assertEqual(result['transactions'][0]['amount'], '-12.34')
        self.assertEqual(len(result['transactions']), 1)
        self.assertTrue(result['provider_pagination_complete'])
        self.assertFalse(result['history_complete'])
        self.assertFalse(result['live'])

    async def test_second_page_redirect_not_followed_and_no_partial_return(self):
        await self.expect_stopped('redirect', 'unexpected_status')

    async def test_second_page_throttle_not_retried_and_no_partial_return(self):
        await self.expect_stopped('throttle', 'rate_limited')

    async def test_second_page_malformed_json_no_partial_return(self):
        await self.expect_stopped('malformed', 'invalid_response')

    async def test_second_page_duplicate_json_keys_no_partial_return(self):
        await self.expect_stopped('duplicate', 'invalid_response')

    async def test_provider_expiry_during_second_response_withholds_both_pages(self):
        await self.expect_stopped('provider_expiry', 'transport_failure')

    async def test_local_expiry_during_second_response_withholds_both_pages(self):
        await self.expect_stopped('local_expiry', 'transport_failure')

    async def test_cancellation_during_second_account_get_propagates_without_retry(self):
        task = asyncio.create_task(self.read(self.build('cancel')))
        try:
            await asyncio.wait_for(self.blocked.wait(), timeout=1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(self.cancelled.is_set())
            self.assertTrue(task.cancelled())
            self.assert_two_pages_only()
        finally:
            if not task.done():
                task.cancel()
            try:
                await task
            except (asyncio.CancelledError, FetchStopped):
                pass


if __name__ == '__main__':
    unittest.main()
