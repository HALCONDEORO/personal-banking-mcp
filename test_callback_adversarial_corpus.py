"""Offline independent contract tests: no socket, key, signature bridge or network.
Run: python -m unittest test_callback_adversarial_corpus
"""
import asyncio,json,unittest
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlencode
from callback_framing import parse_relay_request,relay_request,response_bytes,CallbackRejected,MAX_TARGET,MAX_REQUEST
from callback_receiver import CallbackReceiver
from admin_consent import ConsentAttempt,SetupRejected
C=json.loads((Path(__file__).parent/'tests'/'data'/'callback-contract.json').read_text())
R='https://localhost:8765/callback'
class Reader:
 def __init__(self,chunks):self.chunks=list(chunks);self.sizes=[]
 async def read(self,n):
  self.sizes.append(n)
  if not self.chunks:return b''
  chunk=self.chunks.pop(0)
  if len(chunk)>n:self.chunks.insert(0,chunk[n:]);chunk=chunk[:n]
  await asyncio.sleep(0)
  return chunk
class Writer:
 def __init__(self):self.data=b'';self.closed=False
 def write(self,b):self.data+=b
 async def drain(self):pass
 def close(self):self.closed=True
 async def wait_closed(self):pass
class Tests(unittest.IsolatedAsyncioTestCase):
 def test_manifest(self):
  self.assertEqual(len(C['framing']),29)
  self.assertEqual(len({case['id'] for case in C['framing']}),29)
  self.assertTrue(all(type(case['accept']) is bool for case in C['framing']))
 async def test_declarative_framing(self):
  for c in C['framing']:
   with self.subTest(id=c['id'],component='callback_framing.parse_relay_request'):
    raw=bytes.fromhex(c['hex'])
    if c['accept']:self.assertEqual(parse_relay_request(raw),R.split('/callback')[0]+c['target'])
    else:
     with self.assertRaises(CallbackRejected) as err:parse_relay_request(raw)
     self.assertEqual(str(err.exception),'Callback request rejected')
 async def test_all_prefix_truncations(self):
  raw=relay_request('/callback?state=synthetic&code=synthetic')
  for i in range(len(raw)):
   with self.subTest(prefix_length=i):
    with self.assertRaises(CallbackRejected):parse_relay_request(raw[:i])
 async def test_builder_target_boundaries(self):
  prefix='/callback?x='
  for n in [MAX_TARGET-1,MAX_TARGET]:
   target=prefix+'x'*(n-len(prefix));self.assertEqual(parse_relay_request(relay_request(target)),'https://localhost:8765'+target)
  with self.assertRaises(CallbackRejected):relay_request(prefix+'x'*(MAX_TARGET+1-len(prefix)))
 async def setup_receiver(self):
  a=ConsentAttempt(R);state=a.authorization_body('Synthetic bank','IE',now=datetime(2026,11,20,tzinfo=timezone.utc))['state']
  receiver=CallbackReceiver(a);receiver._future=asyncio.get_running_loop().create_future()
  target='/callback?'+urlencode({'state':state,'code':'synthetic-only-code'})
  return a,receiver,target,state
 async def dispatch(self,r,chunks):
  rd=Reader(chunks);wr=Writer();await r._handle(rd,wr);self.assertTrue(wr.closed);self.assertFalse(r._busy);self.assertEqual(r._tasks,set());return rd,wr
 async def test_receiver_every_fragment_boundary(self):
  # Direct real receiver handler, fake byte reader/writer; no start()/socket.
  _,_,sample,_=await self.setup_receiver();length=len(relay_request(sample))
  for split in range(1,length):
   with self.subTest(split=split,component='callback_receiver.CallbackReceiver._handle'):
    a,r,target,state=await self.setup_receiver();raw=relay_request(target)
    _,w=await self.dispatch(r,[raw[:split],raw[split:]])
    self.assertEqual(r._future.result(),{'code':'synthetic-only-code'});self.assertTrue(a.closed)
    self.assertNotIn(state.encode(),w.data);self.assertNotIn(b'synthetic-only-code',w.data);self.assertIn(b'not confirmed',w.data)
 async def test_receiver_sequence(self):
  a,r,target,state=await self.setup_receiver();raw=relay_request(target)
  _,bad=await self.dispatch(r,[b'malformed']);self.assertIn(b'400',bad.data);self.assertFalse(r._future.done());self.assertFalse(a.closed)
  _,good=await self.dispatch(r,[raw]);self.assertIn(b'200',good.data)
  _,replay=await self.dispatch(r,[raw]);self.assertIn(b'400',replay.data);self.assertEqual(r._future.result(),{'code':'synthetic-only-code'})
 async def test_inconsistent_lifecycle(self):
  for mode in ['cancelled_attempt','cancelled_future','resolved_future','busy','exhausted_connections']:
   with self.subTest(mode=mode):
    a,r,target,state=await self.setup_receiver()
    if mode=='cancelled_attempt':a.cancel()
    elif mode=='cancelled_future':r._future.cancel()
    elif mode=='resolved_future':r._future.set_result({'code':'earlier-synthetic'})
    elif mode=='busy':r._busy=True
    elif mode=='exhausted_connections':r._connections=8
    wr=Writer();await r._handle(Reader([relay_request(target)]),wr);self.assertIn(b'400',wr.data);self.assertTrue(wr.closed)
    if mode=='resolved_future':self.assertEqual(r._future.result(),{'code':'earlier-synthetic'})
    elif mode in ['cancelled_attempt','cancelled_future','exhausted_connections']:self.assertTrue(r._future.cancelled())
 async def test_receiver_body_pipeline_truncation_and_budget(self):
  for mode in ['body','pipeline','missing_last_byte','oversize','reversed_chunks']:
   with self.subTest(mode=mode):
    a,r,target,state=await self.setup_receiver();raw=relay_request(target)
    chunks={'body':[raw,b'X'],'pipeline':[raw,raw],'missing_last_byte':[raw[:-1]],'oversize':[b'x'*(MAX_REQUEST+1)],'reversed_chunks':[raw[12:],raw[:12]]}[mode]
    _,w=await self.dispatch(r,chunks);self.assertIn(b'400',w.data);self.assertFalse(a.closed);self.assertFalse(r._future.done())
 async def test_receiver_eighth_failure_closes_future(self):
  a,r,target,state=await self.setup_receiver()
  for i in range(8):await self.dispatch(r,[b'bad'])
  self.assertTrue(r._future.cancelled());self.assertEqual(r._connections,8)
 async def test_matching_state_invalid_code_burns_attempt(self):
  a,r,target,state=await self.setup_receiver()
  raw=relay_request('/callback?'+urlencode({'state':state,'code':''}));_,w=await self.dispatch(r,[raw]);self.assertIn(b'400',w.data);self.assertTrue(a.closed);self.assertTrue(r._future.cancelled())
 async def test_response_contract(self):
  for accept in [True,False]:
   head,body=response_bytes(accepted=accept).split(b'\r\n\r\n',1)
   self.assertIn(b'Content-Length: '+str(len(body)).encode(),head);self.assertIn(b'Cache-Control: no-store',head);self.assertIn(b'Referrer-Policy: no-referrer',head)
  for bad in [None,1,0,'true']:
   with self.assertRaises(CallbackRejected):response_bytes(accepted=bad)
if __name__=='__main__':unittest.main(verbosity=2)
