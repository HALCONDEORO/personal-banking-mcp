"""Offline independent regression layer for the three-tool fixture contract."""
import asyncio
import json
import random
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import server

class FixtureInvariantTests(unittest.TestCase):
    def test_pagination_date_currency_and_copy_invariants(self):
        rng = random.Random(3671907)
        accounts = server.list_accounts()['data']
        count = 0
        for account in accounts:
            for _ in range(250):
                first = date(2026, 1, 1) + timedelta(days=rng.randrange(0, 10))
                last = first + timedelta(days=rng.randrange(0, 12))
                args = (account['id'], first.isoformat(), last.isoformat())
                whole = server.get_transactions(*args, limit=100)
                limit = rng.randrange(1, 5)
                offset = 0
                rows = []
                for _ in range(10):
                    page = server.get_transactions(*args, limit=limit, offset=offset)
                    self.assertFalse(page['live'])
                    self.assertEqual(page['source'], 'synthetic-fixtures')
                    self.assertEqual(page['complete'], page['next_offset'] is None)
                    self.assertLessEqual(len(page['data']), limit)
                    rows.extend(page['data'])
                    if page['next_offset'] is None:
                        break
                    self.assertGreater(page['next_offset'], offset)
                    offset = page['next_offset']
                else:
                    self.fail('Pagination did not terminate')
                self.assertEqual(rows, whole['data'])
                self.assertEqual(len({t['id'] for t in rows}), len(rows))
                for row in rows:
                    self.assertEqual(row['account'], account['id'])
                    self.assertEqual(row['currency'], account['currency'])
                    self.assertTrue(first.isoformat() <= row['date'] <= last.isoformat())
                    self.assertIn(row['status'], ('booked', 'pending'))
                if rows:
                    rows[0]['description'] = 'mutated result only'
                    self.assertNotEqual(rows, server.get_transactions(*args, limit=100)['data'])
                count += 1
        self.assertEqual(count, 500)

    def test_inclusive_day_limit_and_leap_calendar(self):
        for start in (date(2024, 1, 1), date(2024, 2, 29), date(2025, 1, 1)):
            for days in (0, 364, 365):
                result = server.get_transactions('demo-eur', start.isoformat(), (start + timedelta(days=days)).isoformat())
                self.assertFalse(result['live'])
            with self.assertRaises(ValueError):
                server.get_transactions('demo-eur', start.isoformat(), (start + timedelta(days=366)).isoformat())

    def test_fixture_reads_never_attempt_socket_io(self):
        def denied(*args, **kwargs):
            raise AssertionError('Unexpected network operation')
        with patch('socket.socket.connect', denied), patch('socket.socket.bind', denied), patch('socket.getaddrinfo', denied):
            for item in server.list_accounts()['data']:
                server.get_balance(item['id'])
                server.get_transactions(item['id'], '2026-01-01', '2026-01-31')

    def test_bank_environment_cannot_enable_a_live_adapter(self):
        async def run():
            parameters = StdioServerParameters(command=sys.executable,
                args=[str(Path(server.__file__).resolve())], env={
                    'BANKING_ADAPTER': 'enablebanking',
                    'ENABLE_BANKING_APP_ID': 'synthetic-invalid-app',
                    'ENABLE_BANKING_KEY_PATH': '/nonexistent/synthetic-key.pem',
                    'ENABLE_BANKING_SANDBOX': 'false',
                })
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    self.assertEqual({t.name for t in (await client.list_tools()).tools},
                        {'list_accounts', 'get_balance', 'get_transactions', 'search_transactions', 'summarize_transactions'})
                    for name, args in [('list_accounts', {}), ('get_balance', {'account': 'demo-eur'}),
                        ('get_transactions', {'account': 'demo-eur', 'start': '2026-01-01', 'end': '2026-01-31'})]:
                        result = await client.call_tool(name, args)
                        self.assertFalse(result.isError)
                        data = json.loads(result.content[0].text)
                        self.assertIs(data['live'], False)
                        self.assertEqual(data['source'], 'synthetic-fixtures')
        asyncio.run(run())

if __name__ == '__main__':
    unittest.main()
