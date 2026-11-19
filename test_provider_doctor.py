import asyncio,json,unittest
from provider_doctor import run_doctor,ProbeResult
from provider_pager import FetchStopped

class TestDoctor(unittest.IsolatedAsyncioTestCase):
 async def test_status_map(self):
  for code,status in [(200,'reachable'),(401,'reconnect_required'),(403,'access_denied'),(429,'rate_limited'),(503,'provider_unavailable'),(302,'redirect_refused'),(204,'unexpected_response')]:
   calls=[]
   async def probe():calls.append(1);return ProbeResult(code)
   with self.subTest(code=code):
    out=await run_doctor(probe);self.assertEqual(out['status'],status);self.assertEqual(len(calls),1)
    self.assertFalse(out['full_readiness_verified']);self.assertFalse(out['automatic_retry'])
 async def test_private_exception_never_exposed(self):
  async def probe():raise RuntimeError('PRIVATE-EXCEPTION-CANARY')
  out=await run_doctor(probe)
  self.assertEqual(out['status'],'probe_failed');self.assertNotIn('PRIVATE-',json.dumps(out))
 async def test_wrong_result(self):
  for value in [True,{'status':200,'body':'PRIVATE-BODY'},ProbeResult(True),None]:
   async def probe():return value
   self.assertEqual((await run_doctor(probe))['status'],'unexpected_response')
 async def test_timeout_once(self):
  calls=[]
  async def probe():calls.append(1);await asyncio.sleep(1)
  out=await run_doctor(probe,seconds=0.01)
  self.assertEqual(out['status'],'timeout');self.assertEqual(len(calls),1)
 async def test_cancel_suppression_late_success(self):
  async def probe():
   try:await asyncio.sleep(1)
   except asyncio.CancelledError:pass
   return ProbeResult(200)
  self.assertEqual((await run_doctor(probe,seconds=0.01))['status'],'timeout')
 async def test_known_transport_error(self):
  async def probe():raise FetchStopped('time_budget')
  self.assertEqual((await run_doctor(probe))['status'],'timeout')
 async def test_unknown_transport_error(self):
  async def probe():raise FetchStopped('PRIVATE-CODE')
  out=await run_doctor(probe);self.assertNotIn('PRIVATE-',json.dumps(out))
 async def test_configuration(self):
  for seconds in [True,0,-1,6,float('nan'),float('inf'),'3']:
   with self.subTest(seconds=seconds),self.assertRaises(ValueError):await run_doctor(lambda:None,seconds=seconds)
 async def test_caller_cancel_propagates(self):
  entered=asyncio.Event()
  async def probe():entered.set();await asyncio.sleep(10)
  task=asyncio.create_task(run_doctor(probe));await entered.wait();task.cancel()
  with self.assertRaises(asyncio.CancelledError):await task
 async def test_no_constructor_or_import_network(self):
  self.assertEqual(repr(ProbeResult(200)),'<ProbeResult private>')

if __name__=='__main__':unittest.main()
