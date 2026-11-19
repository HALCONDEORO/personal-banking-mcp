import asyncio
import json
import unittest
from unittest.mock import patch
import server
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys

ARGS=('demo-eur','2026-01-01','2026-01-10')
class WiringTests(unittest.TestCase):
 def test_projection_exact_eight_fields(self):
  records=server._analysis_rows(*ARGS)
  self.assertTrue(records)
  for row in records:self.assertEqual(set(row),{'amount','currency','currency_known','status','date','date_source','date_inferred','description'})
 def test_search(self):
  r=server.search_transactions(*ARGS,query='REFUND');self.assertFalse(r['live']);self.assertEqual(r['data']['matched_in_input'],1)
 def test_summary(self):
  r=server.summarize_transactions(*ARGS);totals=r['data']['totals'];self.assertEqual([x['net'] for x in totals],['87.60','-9.99']);self.assertEqual(r['data']['history_completeness'],'not_verified')
 def test_gbp_separate(self):self.assertEqual(server.summarize_transactions('demo-gbp',*ARGS[1:])['data']['totals'][0]['currency'],'GBP')
 def test_empty_scope(self):self.assertEqual(server.summarize_transactions('demo-eur','2025-01-01','2025-01-02')['data']['totals'],[])
 def test_no_socket_io(self):
  with patch('socket.socket.connect',side_effect=AssertionError),patch('socket.socket.bind',side_effect=AssertionError),patch('socket.getaddrinfo',side_effect=AssertionError):
   server.search_transactions(*ARGS);server.summarize_transactions(*ARGS)
 def test_incomplete_refuses_no_truncation_guess(self):
  with patch.object(server,'get_transactions',return_value={'data':[],'complete':False}),self.assertRaises(ValueError):server._analysis_rows(*ARGS)
 def test_invalid_account_and_dates(self):
  for tool in [server.search_transactions,server.summarize_transactions]:
   for args in [('unknown',*ARGS[1:]),('demo-eur','2026-02-30','2026-03-01'),('demo-eur','2026-02-01','2026-01-01')]:
    with self.subTest(tool=tool,args=args),self.assertRaises(ValueError):tool(*args)
 def test_description_inert_not_evaluated(self):
  text='SYNTHETIC-UNTRUSTED-TEXT'
  with patch.object(server,'_MOVEMENTS',(dict(server._MOVEMENTS[0],description=text),)):
   r=server.search_transactions(*ARGS,query=text);self.assertEqual(r['data']['transactions'][0]['description'],text)
 def test_no_shared_rows(self):
  r=server.search_transactions(*ARGS);r['data']['transactions'][0]['description']='changed';self.assertNotEqual(server.search_transactions(*ARGS)['data']['transactions'][0]['description'],'changed')
 def test_stdio_new_tools_and_strict_inputs(self):
  async def run():
   params=StdioServerParameters(command=sys.executable,args=[server.__file__],env={})
   async with stdio_client(params) as (read,write):
    async with ClientSession(read,write) as client:
     await client.initialize();tools=(await client.list_tools()).tools
     self.assertEqual(len(tools),5);self.assertTrue(all(t.annotations.readOnlyHint and not t.annotations.destructiveHint for t in tools))
     args={'account':ARGS[0],'start':ARGS[1],'end':ARGS[2]}
     for tool in ['search_transactions','summarize_transactions']:
      result=await client.call_tool(tool,args);self.assertFalse(result.isError);self.assertIs(json.loads(result.content[0].text)['live'],False)
     for change in [{'limit':True},{'limit':2.0},{'limit':'2'},{'limit':101},{'query':5},{'query':'x'*257}]:
      result=await client.call_tool('search_transactions',args|change);self.assertTrue(result.isError)
  asyncio.run(run())
if __name__=='__main__':unittest.main()
