"""Independent regressions. Only synthetic fixtures and a local stdio process."""
import asyncio
import json
import sys
import unittest
from unittest.mock import patch
import server
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class ReviewTests(unittest.TestCase):
    def test_additional_path_and_origin_negatives(self):
        for method, host, path in [
            ('HEAD', server.BANK_HOST, '/sessions/demo'),
            ('GET', server.BANK_HOST, '/auth'),
            ('POST', server.BANK_HOST, '/sessions/demo'),
            ('GET', server.BANK_HOST, '/accounts/x/transactions#fragment'),
            ('GET', server.BANK_HOST, '/accounts/x/transactions%3Ffoo'),
            ('GET', 'https://api.enablebanking.com:443', '/sessions/demo'),
            ('GET', 'https://user@api.enablebanking.com', '/sessions/demo'),
        ]:
            with self.subTest(method=method, host=host, path=path):
                with self.assertRaises(PermissionError):
                    server.read_request_policy(method, host, path)

    def test_description_is_returned_as_untrusted_fixture_data(self):
        text = 'Synthetic fixture note, not an instruction or a bank record.'
        row = dict(server._MOVEMENTS[0], description=text)
        with patch.object(server, '_MOVEMENTS', (row,)):
            result = server.get_transactions('demo-eur', '2026-01-01', '2026-01-10')
        self.assertEqual(result['data'][0]['description'], text)
        self.assertFalse(result['live'])
        self.assertIn('untrusted', result['note'])

    def test_protocol_rejects_coerced_pagination(self):
        async def run():
            params = StdioServerParameters(command=sys.executable, args=['server.py'], env={})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    for field in ('limit', 'offset'):
                        for value in (True, False, '2', 2.0, None):
                            args = dict(account='demo-eur', start='2026-01-01', end='2026-01-10')
                            args[field] = value
                            result = await client.call_tool('get_transactions', args)
                            self.assertTrue(result.isError, (field, value))
                    result = await client.call_tool('get_transactions', dict(
                        account='demo-eur', start='2026-01-01', end='2026-01-10', limit=2, offset=0))
                    self.assertFalse(result.isError)
                    self.assertEqual(len(json.loads(result.content[0].text)['data']), 2)
        asyncio.run(run())

if __name__ == '__main__':
    unittest.main()
