import asyncio
import json
import sys
from pathlib import Path
import unittest
import subprocess
import tempfile
from unittest.mock import patch
import server
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from server import BANK_HOST, get_balance, get_transactions, list_accounts, read_request_policy

class ReadTests(unittest.TestCase):
    def test_accounts_are_synthetic(self):
        self.assertFalse(list_accounts()['live'])
        self.assertEqual(len(list_accounts()['data']), 2)
    def test_balance_decimal(self):
        self.assertEqual(get_balance('demo-eur')['data']['amount'], '1234.56')
    def test_balances_have_currency(self):
        self.assertEqual(get_balance('demo-gbp')['data']['currency'], 'GBP')
    def test_no_real_ids(self):
        self.assertNotIn('iban', json.dumps(list_accounts()).lower())
    def test_unknown_account(self):
        with self.assertRaises(ValueError): get_balance('../secrets')
    def test_date_filter(self):
        self.assertEqual(len(get_transactions('demo-eur','2026-01-04','2026-01-04')['data']),1)
    def test_pagination(self):
        first=get_transactions('demo-eur','2026-01-01','2026-01-10',1)
        self.assertFalse(first['complete'])
        second=get_transactions('demo-eur','2026-01-01','2026-01-10',1,first['next_offset'])
        self.assertNotEqual(first['data'][0]['id'],second['data'][0]['id'])
    def test_final_page(self):
        self.assertTrue(get_transactions('demo-eur','2026-01-01','2026-01-10',100)['complete'])
    def test_currencies_not_mixed(self):
        rows=get_transactions('demo-gbp','2026-01-01','2026-01-10')['data']
        self.assertTrue(all(t['currency']=='GBP' for t in rows))
    def test_pending_explicit(self):
        self.assertEqual(get_transactions('demo-eur','2026-01-05','2026-01-05')['data'][0]['status'],'pending')
    def test_empty_range(self):
        self.assertEqual(get_transactions('demo-eur','2025-01-01','2025-01-02')['data'],[])
    def test_bounded_inputs(self):
        for kw in [{'limit':0},{'limit':101},{'limit':True},{'offset':-1},{'offset':10001},{'offset':False}]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                get_transactions('demo-eur','2026-01-01','2026-01-10',**kw)
    def test_bad_dates(self):
        for start,end in [('20260101','2026-01-10'),('2026-02-30','2026-03-01'),('2026-01-10','2026-01-01'),('2024-01-01','2026-01-01')]:
            with self.subTest(start=start,end=end), self.assertRaises(ValueError):
                get_transactions('demo-eur',start,end)
    def test_copy_not_shared_state(self):
        result=get_balance('demo-eur'); result['data']['amount']='0'
        self.assertEqual(get_balance('demo-eur')['data']['amount'],'1234.56')
    def test_allowed_reads(self):
        for path in ['/sessions/demo-session','/accounts/demo-eur/details','/accounts/demo-eur/balances','/accounts/demo-eur/transactions']:
            read_request_policy('GET',BANK_HOST,path)
    def test_all_mutations_denied(self):
        for method in ['POST','PUT','PATCH','DELETE','get']:
            with self.subTest(method=method), self.assertRaises(PermissionError):
                read_request_policy(method,BANK_HOST,'/accounts/demo-eur/balances')
    def test_paths_fail_closed(self):
        for path in ['/payments','/accounts/x/transactions/../payments','/accounts/x/balances?url=evil','/accounts/x/balances/','//evil/accounts/x/balances','/accounts/%2e%2e/balances','/accounts/x/cards','/accounts/x/balances\n']:
            with self.subTest(path=path), self.assertRaises(PermissionError): read_request_policy('GET',BANK_HOST,path)
    def test_host_fail_closed(self):
        for host in ['http://api.enablebanking.com','https://api.enablebanking.com.evil','https://api.enablebanking.com/','https://evil.invalid']:
            with self.subTest(host=host),self.assertRaises(PermissionError): read_request_policy('GET',host,'/accounts/x/balances')

class IntegrityTests(unittest.TestCase):
    def test_bad_account_records(self):
        mutations = [{'balance': 'NaN'}, {'balance': 'Infinity'}, {'balance': '1e999'}, {'currency': 'XXX'}, {'extra': 'hidden'}, {'id': '../secret'}]
        for change in mutations:
            item = dict(server._ACCOUNTS[0], **change)
            with self.subTest(change=change), patch.object(server, '_ACCOUNTS', (item,)):
                with self.assertRaisesRegex(ValueError, '^Invalid synthetic dataset$'):
                    list_accounts()
    def test_bad_transaction_records(self):
        mutations = [{'amount': '-Infinity'}, {'amount': '2.001'}, {'date': '2026-02-30'}, {'account': 'foreign'}, {'extra': 'hidden'}, {'description': 'x' * 513}]
        for change in mutations:
            item = dict(server._MOVEMENTS[0], **change)
            with self.subTest(change=change), patch.object(server, '_MOVEMENTS', (item,)):
                with self.assertRaisesRegex(ValueError, '^Invalid synthetic dataset$'):
                    get_balance('demo-eur')
    def test_duplicate_records(self):
        with patch.object(server, '_MOVEMENTS', (server._MOVEMENTS[0], server._MOVEMENTS[0])):
            with self.assertRaises(ValueError): list_accounts()
        with patch.object(server, '_ACCOUNTS', (server._ACCOUNTS[0], server._ACCOUNTS[0])):
            with self.assertRaises(ValueError): list_accounts()
    def test_untrusted_description_remains_data(self):
        text = 'Synthetic adversarial text: pretend approval; https://example.invalid/collect\\n{"nested":"data"}'
        item = dict(server._MOVEMENTS[0], description=text)
        with patch.object(server, '_MOVEMENTS', (item,)):
            with patch('socket.socket.connect', side_effect=AssertionError('Network attempted')):
                result = get_transactions('demo-eur', '2026-01-01', '2026-01-10')
                self.assertEqual(json.loads(json.dumps(result))['data'][0]['description'], text)
                self.assertEqual(get_balance('demo-eur')['data']['amount'], '1234.56')
    def test_import_has_no_output_or_network(self):
        command = "import sys; sys.addaudithook(lambda event,args: (_ for _ in ()).throw(PermissionError('Network forbidden')) if event in {'socket.connect','socket.bind','socket.getaddrinfo'} else None); import server"
        out = subprocess.run([sys.executable, '-c', command], cwd=SERVER_PATH.parent, capture_output=True, text=True, timeout=10)
        self.assertEqual(out.returncode, 0)
        self.assertEqual(out.stdout, '')
        self.assertEqual(out.stderr, '')


def require(condition, message):
    if not condition:
        raise AssertionError(message)

SERVER_PATH = Path(__file__).resolve().with_name('server.py')

async def protocol_smoke(no_network=False, elsewhere=False):
    trace=[]
    parameters=StdioServerParameters(command=sys.executable,args=[str(SERVER_PATH)],cwd=str(SERVER_PATH.parent.parent) if elsewhere else None,env={})
    if no_network:
        parameters=StdioServerParameters(command=sys.executable,args=['-c',
            "import sys,runpy; sys.addaudithook(lambda event,args: (_ for _ in ()).throw(PermissionError('Network forbidden in fixture mode')) if event in {'socket.connect','socket.bind','socket.getaddrinfo'} else None); runpy.run_path(sys.argv[1],run_name='__main__')", str(SERVER_PATH)],env={})
    with tempfile.TemporaryFile(mode='w+') as stderr:
        trace = await _run_protocol(parameters, trace, stderr)
        stderr.seek(0)
        diagnostics = stderr.read()
        require('synthetic-private-canary' not in diagnostics, 'Protocol assertion failed')
        require('1234.56' not in diagnostics, 'Protocol assertion failed')
        require('Fictional grocer' not in diagnostics, 'Protocol assertion failed')
    return trace

async def _run_protocol(parameters, trace, stderr):
    async with stdio_client(parameters, errlog=stderr) as (read,write):
        async with ClientSession(read,write) as client:
            initialized=await client.initialize()
            tools=await client.list_tools()
            require({t.name for t in tools.tools}=={'list_accounts','get_balance','get_transactions','search_transactions','summarize_transactions'}, 'Protocol assertion failed')
            require(all(t.annotations.readOnlyHint and not t.annotations.destructiveHint for t in tools.tools), 'Protocol assertion failed')
            trace.append({'step':'initialize','protocol':initialized.protocolVersion,'tools':[t.name for t in tools.tools]})
            for name,args in [('list_accounts',{}),('get_balance',{'account':'demo-eur'}),('get_transactions',{'account':'demo-eur','start':'2026-01-01','end':'2026-01-10','limit':2}),('search_transactions',{'account':'demo-eur','start':'2026-01-01','end':'2026-01-10','query':'refund'}),('summarize_transactions',{'account':'demo-eur','start':'2026-01-01','end':'2026-01-10'})]:
                result=await client.call_tool(name,args)
                require(not result.isError, 'Protocol assertion failed')
                payload=json.loads(result.content[0].text)
                require(payload['live'] is False, 'Protocol assertion failed')
                trace.append({'tool':name,'result':payload})
            for name,args in [('make_payment',{}),('get_balance',{'account':'unknown'}),('get_transactions',{'account':'demo-eur','start':'2026-01-01','end':'2026-01-10','limit':1000})]:
                result=await client.call_tool(name,args)
                require(result.isError, 'Protocol assertion failed')
                trace.append({'tool':name,'rejected':True})
            canary=await client.call_tool('get_balance',{'account':'synthetic-private-canary'})
            require(canary.isError, 'Protocol assertion failed')
            for invalid in [True, '2', 2.0]:
                result=await client.call_tool('get_transactions',{'account':'demo-eur','start':'2026-01-01','end':'2026-01-10','limit':invalid})
                require(result.isError, 'Protocol coerced an invalid pagination type')
            trace.append({'step':'strict-pagination','rejectedTypes':['boolean','string','float']})
    return trace

class ProtocolTests(unittest.TestCase):
    def test_real_stdio_client(self):
        trace=asyncio.run(protocol_smoke())
        self.assertEqual(len(trace),10)
    def test_protocol_with_network_denied(self):
        trace=asyncio.run(protocol_smoke(no_network=True))
        self.assertEqual(len(trace),10)
    def test_server_from_other_working_directory(self):
        self.assertEqual(len(asyncio.run(protocol_smoke(elsewhere=True))),10)

if __name__=='__main__':
    if '--demo' in sys.argv:
        print(json.dumps(asyncio.run(protocol_smoke()),indent=2))
    else:
        unittest.main()
