# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Synthetic composition: pager -> session gate -> real read client -> mock HTTP.

This joins existing isolated layers without wiring them to MCP. The only HTTP
transport is httpx.MockTransport. No real JWT, credentials, registration,
Windows, bank consent or network request. Positive controls prevent an
always-rejecting composition from looking correct. Consent checks are not
atomic; mock success proves no live-bank compatibility or activation authority.
"""
import json
import unittest
from datetime import datetime, timezone, timedelta

import httpx
from provider_checked_session import CheckedSessionRead
from provider_http import ReadOnlyHTTP
from provider_pager import fetch_simulated_transactions, FetchStopped
from provider_session import PrivateSession

SID = '11111111-1111-4111-8111-111111111111'
AID = '22222222-2222-4222-8222-222222222222'
NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)


class CheckedHTTPStackTests(unittest.IsolatedAsyncioTestCase):
    def build(self, *, second_status='AUTHORIZED', http_status=200):
        self.calls, self.tokens = [], []
        self.checks, self.pages = 0, 0
        self.first_page_rows = []

        async def handler(request):
            self.calls.append(request)
            if request.url.path == '/sessions/' + SID:
                self.checks += 1
                payload = {
                    'status': 'AUTHORIZED' if self.checks == 1 else second_status,
                    'psu_type': 'personal',
                    'aspsp': {'name': 'Synthetic bank', 'country': 'IE'},
                    'access': {'valid_until': (NOW + timedelta(hours=1)).isoformat()},
                    'accounts': [AID],
                }
                status = http_status
            else:
                self.pages += 1
                rows = ([{'transaction_amount': {'amount': '12.34', 'currency': 'EUR'},
                          'credit_debit_indicator': 'DBIT', 'status': 'BOOK',
                          'transaction_date': '2026-11-01',
                          'remittance_information': ['SYNTHETIC-PARTIAL-ROW']}]
                        if self.pages == 1 else [])
                if self.pages == 1:
                    self.first_page_rows = rows
                payload = {'transactions': rows, 'continuation_key':
                           'https://synthetic.invalid/opaque' if self.pages == 1 else None}
                status = 200
            return httpx.Response(status, headers={'content-type': 'application/json'},
                                  stream=httpx.ByteStream(json.dumps(payload).encode()))

        def token():
            self.tokens.append(True)
            return 'synthetic.synthetic.synthetic'

        http = ReadOnlyHTTP(token, accounts=frozenset([AID]), session=SID,
                            _test_transport=httpx.MockTransport(handler))
        return CheckedSessionRead(
            session=PrivateSession(SID, (AID,), NOW + timedelta(hours=2)),
            bank='Synthetic bank', country='IE', transport=http, now=lambda: NOW)

    async def run_pager(self, reader):
        return await fetch_simulated_transactions(
            AID, frozenset([AID]), '2026-11-01', '2026-11-20', reader)

    async def test_positive_two_pages_recheck_before_each_get(self):
        result = await self.run_pager(self.build())
        self.assertEqual((self.checks, self.pages, len(self.tokens)), (2, 2, 4))
        self.assertEqual([request.url.path for request in self.calls],
                         ['/sessions/' + SID, '/accounts/' + AID + '/transactions'] * 2)
        self.assertTrue(all(request.method == 'GET' for request in self.calls))
        self.assertTrue(all(request.url.host == 'api.enablebanking.com' for request in self.calls))
        self.assertEqual(self.calls[-1].url.params['continuation_key'],
                         'https://synthetic.invalid/opaque')
        self.assertEqual(result['pages'], 2)
        self.assertTrue(result['provider_pagination_complete'])
        self.assertFalse(result['live'])
        self.assertFalse(result['history_complete'])
        self.assertEqual(len(result['transactions']), 1)
        self.assertEqual(result['transactions'][0]['amount'], '-12.34')
        self.assertEqual(result['transactions'][0]['description'], 'SYNTHETIC-PARTIAL-ROW')

    async def test_revoked_second_check_stops_before_second_account_get(self):
        with self.assertRaises(FetchStopped) as error:
            await self.run_pager(self.build(second_status='REVOKED'))
        self.assertEqual(error.exception.args, ('transport_failure',))
        self.assertEqual(len(self.first_page_rows), 1)
        self.assertEqual(self.first_page_rows[0]['remittance_information'], ['SYNTHETIC-PARTIAL-ROW'])
        self.assertNotIn('SYNTHETIC-PARTIAL-ROW', str(error.exception))
        self.assertEqual((self.checks, self.pages, len(self.tokens)), (2, 1, 3))
        self.assertEqual([request.url.path for request in self.calls],
                         ['/sessions/' + SID, '/accounts/' + AID + '/transactions',
                          '/sessions/' + SID])

    async def test_session_http_throttle_makes_no_account_get_or_retry(self):
        with self.assertRaises(FetchStopped) as error:
            await self.run_pager(self.build(http_status=429))
        self.assertEqual(error.exception.args, ('transport_failure',))
        self.assertEqual((self.checks, self.pages, len(self.tokens)), (1, 0, 1))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0].url.path, '/sessions/' + SID)


if __name__ == '__main__':
    unittest.main()
