"""Synthetic integration only. No external bank, TLS, Windows or SSH calls.

Requires reviewed admin_consent, callback_framing, callback_receiver, admin_http,
provider_session and private_store modules at the import root. All provider HTTP
is httpx.MockTransport; the only real sockets are ephemeral IPv4 loopback.
"""
import asyncio,contextlib,io,json,logging,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
import httpx
from admin_consent import ConsentAttempt,SetupRejected
from admin_http import AdminAISHTTP,AdminStopped
from callback_framing import relay_request
from callback_receiver import CallbackReceiver
from provider_session import validate_created_session,SessionRejected
from private_store import PrivateStore,PrivateStoreError

REDIRECT='https://localhost:8765/callback'
BANK='Synthetic selected bank'
COUNTRY='IE'
ACCOUNT='22222222-2222-4222-8222-222222222222'
SESSION='11111111-1111-4111-8111-111111111111'
TOKEN='synthetic.synthetic.synthetic'
AUTH_URL='https://auth.enablebanking.com/ais/start?sessionid='+SESSION

class Stream(httpx.AsyncByteStream):
 def __init__(self,data):self.data=data
 async def __aiter__(self):yield self.data

class TestSyntheticAdminIntegration(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.now=datetime.now(timezone.utc)
  self.attempt=ConsentAttempt(REDIRECT)
  self.body=self.attempt.authorization_body(BANK,COUNTRY,now=self.now)
  self.until=datetime.fromisoformat(self.body['access']['valid_until'])
  self.calls=[];self.override=None
  def handle(request):
   self.calls.append((request.method,request.url.path))
   self.assertEqual(request.url.host,'api.enablebanking.com')
   if request.url.path=='/auth':response={'url':AUTH_URL}
   elif request.url.path=='/sessions':
    self.assertEqual(json.loads(request.content),{'code':'SYNTHETIC-PRIVATE-CODE'})
    response=self.override if self.override is not None else {
     'session_id':SESSION,'accounts':[{'uid':ACCOUNT,'account_id':{'iban':'SYNTHETIC-PRIVATE-IBAN'}}],
     'psu_type':'personal','aspsp':{'name':BANK,'country':COUNTRY},
     'access':{'valid_until':self.until.isoformat()}}
   else:self.fail('Unplanned endpoint')
   return httpx.Response(200,headers={'content-type':'application/json'},stream=Stream(json.dumps(response).encode()))
  self.http=AdminAISHTTP(lambda:TOKEN,_test_transport=httpx.MockTransport(handle))
  self.receiver=CallbackReceiver(self.attempt,port=0,read_seconds=0.1,lifetime_seconds=1)
  await self.receiver.start();self.port=self.receiver.port
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'private'
  self.store=PrivateStore(str(self.path))
 async def asyncTearDown(self):
  await self.receiver.close();self.store.close();self.tmp.cleanup()
 async def send_callback(self,state=None):
  target='/callback?'+urlencode({'state':state if state is not None else self.body['state'],'code':'SYNTHETIC-PRIVATE-CODE'})
  reader,writer=await asyncio.open_connection('127.0.0.1',self.port)
  writer.write(relay_request(target));await writer.drain();writer.write_eof()
  response=await asyncio.wait_for(reader.read(),1);writer.close();await writer.wait_closed()
  return response
 async def completed_local_flow(self):
  auth=(await self.http.start_authorization(self.body)).take()
  self.assertEqual(auth,{'url':AUTH_URL})
  pending=asyncio.create_task(self.receiver.wait_private_result())
  response=await self.send_callback()
  code_body=await pending
  reply=(await self.http.exchange_code(code_body)).take()
  session=validate_created_session(reply,selected_bank=BANK,selected_country=COUNTRY,requested_until=self.until,now=self.now)
  private_session,accounts=session.transport_ids(now=self.now)
  # Minimal private persistence, not a public output or real production schema.
  self.store.write('session.json',json.dumps({'session_id':private_session,'accounts':list(accounts),
      'valid_until':session.summary(now=self.now)['valid_until']}).encode())
  return response,session
 async def test_complete_synthetic_flow_no_private_stdout_or_logs(self):
  output=io.StringIO();handler=logging.StreamHandler(output);root=logging.getLogger();previous=root.level
  root.addHandler(handler);root.setLevel(logging.DEBUG)
  try:
   with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):response,session=await self.completed_local_flow()
  finally:root.removeHandler(handler);root.setLevel(previous)
  visible=output.getvalue()+response.decode()+repr(session)+repr(self.http)
  for value in [self.body['state'],'SYNTHETIC-PRIVATE-CODE','SYNTHETIC-PRIVATE-IBAN',TOKEN,SESSION,ACCOUNT]:
   self.assertNotIn(value,visible)
  stored=json.loads(self.store.read('session.json'))
  self.assertEqual(stored['session_id'],SESSION);self.assertNotIn('iban',json.dumps(stored))
  self.assertEqual(self.calls,[('POST','/auth'),('POST','/sessions')])
  self.assertEqual(session.summary(now=self.now)['live_consent_status'],'not_verified')
 async def test_wrong_state_never_exchanges_or_persists(self):
  await self.http.start_authorization(self.body)
  response=await self.send_callback(state='WRONG-SYNTHETIC-STATE')
  self.assertIn(b'400 Bad Request',response);self.assertEqual(self.calls,[('POST','/auth')])
  with self.assertRaises(PrivateStoreError):self.store.read('session.json')
 async def test_invalid_session_does_not_persist(self):
  self.override={'session_id':SESSION,'accounts':[],'psu_type':'personal','aspsp':{'name':BANK,'country':COUNTRY},'access':{'valid_until':self.until.isoformat()}}
  with self.assertRaises(SessionRejected):await self.completed_local_flow()
  with self.assertRaises(PrivateStoreError):self.store.read('session.json')
 async def test_bank_mismatch_does_not_persist(self):
  self.override={'session_id':SESSION,'accounts':[{'uid':ACCOUNT}],'psu_type':'personal','aspsp':{'name':'Other synthetic bank','country':COUNTRY},'access':{'valid_until':self.until.isoformat()}}
  with self.assertRaises(SessionRejected):await self.completed_local_flow()
  with self.assertRaises(PrivateStoreError):self.store.read('session.json')
 async def test_replay_cannot_reach_exchange(self):
  await self.completed_local_flow()
  with self.assertRaises(OSError):await self.send_callback()
  self.assertEqual(self.calls,[('POST','/auth'),('POST','/sessions')])

if __name__=='__main__':unittest.main()
