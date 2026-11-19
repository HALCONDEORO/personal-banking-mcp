import asyncio,json,traceback,unittest
from datetime import datetime,timezone
from unittest.mock import patch
import httpx
from admin_http import AdminAISHTTP,AdminStopped,PrivateReply,MAX_BYTES
from admin_consent import ConsentAttempt

TOKEN='synthetic.synthetic.synthetic'
URL='https://auth.enablebanking.com/ais/start?sessionid=11111111-1111-4111-8111-111111111111'
class Stream(httpx.AsyncByteStream):
 def __init__(self,data):self.data=data
 async def __aiter__(self):yield self.data

class TestAdminHTTP(unittest.IsolatedAsyncioTestCase):
 def client(self,reply,**extra):
  self.requests=[]
  def handle(request):
   self.requests.append(request)
   r=reply(request)
   if r.is_stream_consumed:return httpx.Response(r.status_code,headers=r.headers,stream=Stream(r.content))
   return r
  return AdminAISHTTP(lambda:TOKEN,_test_transport=httpx.MockTransport(handle),**extra)
 def body(self):return ConsentAttempt('https://localhost:8765/callback').authorization_body('Selected synthetic bank','IE',now=datetime.now(timezone.utc))
 async def test_auth_post_once(self):
  c=self.client(lambda r:httpx.Response(200,json={'url':URL,'authorization_id':'private'}))
  result=await c.start_authorization(self.body())
  self.assertEqual(repr(result),'<PrivateReply private>');self.assertEqual(result.take(),{'url':URL})
  with self.assertRaises(AdminStopped):result.take()
  self.assertEqual(len(self.requests),1);r=self.requests[0]
  self.assertEqual(r.method,'POST');self.assertEqual(str(r.url),'https://api.enablebanking.com/auth')
  self.assertNotIn(TOKEN,str(r.url));self.assertEqual(r.headers['authorization'],'Bearer '+TOKEN)
 async def test_exchange_private(self):
  c=self.client(lambda r:httpx.Response(200,json={'session_id':'SYNTHETIC-PRIVATE'}))
  result=await c.exchange_code({'code':'SYNTHETIC-CODE'})
  self.assertEqual(result.take()['session_id'],'SYNTHETIC-PRIVATE')
  self.assertEqual(str(self.requests[0].url),'https://api.enablebanking.com/sessions')
 async def test_no_other_paths_before_token(self):
  c=AdminAISHTTP(lambda:self.fail('token accessed'))
  for path in ['/payments','/sessions/x','https://evil.test','/auth?x=y']:
   with self.assertRaises(AdminStopped):await c._post(path,{'code':'synthetic'})
 async def test_invalid_body_before_http(self):
  c=self.client(lambda r:self.fail('HTTP accessed'))
  for body in [{'code':''},{'code':True},{'code':'a\nprivate'},{'code':'x','payments':[]}]:
   with self.assertRaises(AdminStopped):await c.exchange_code(body)
  b=self.body();b['psu_type']='business'
  with self.assertRaises(AdminStopped):await c.start_authorization(b)
  self.assertFalse(self.requests)
 async def test_serialized_size_before_token(self):
  calls=[]
  def token():calls.append(1);return TOKEN
  c=AdminAISHTTP(token,_test_transport=httpx.MockTransport(lambda r:self.fail('HTTP accessed')))
  body={'code':chr(34)*4096}
  with self.assertRaises(AdminStopped):await c.exchange_code(body)
  self.assertEqual(calls,[])
 async def test_redirect_error_no_retry_no_body(self):
  class NeverRead(httpx.AsyncByteStream):
   async def __aiter__(self):raise AssertionError('Error body read');yield b''
  for status in [301,302,400,401,403,429,500]:
   c=self.client(lambda r:httpx.Response(status,headers={'location':'https://evil.test'},stream=NeverRead()))
   with self.assertRaises(AdminStopped):await c.exchange_code({'code':'synthetic'})
   self.assertEqual(len(self.requests),1)
 async def test_auth_url_policy(self):
  for url in ['http://auth.enablebanking.com/ais/start?x=1','https://evil.test/ais/start?x=1','https://auth.enablebanking.com@evil.test/ais/start?x=1',URL+'#private','https://auth.enablebanking.com/ais/start?x=1&x=2']:
   c=self.client(lambda r:httpx.Response(200,json={'url':url}))
   with self.assertRaises(AdminStopped):await c.start_authorization(self.body())
 async def test_duplicate_json_nan_deep(self):
  for raw in [b'{"private":"CANARY","private":"x"}',b'{"x":NaN}',b'['*2000+b'0'+b']'*2000]:
   c=self.client(lambda r:httpx.Response(200,content=raw,headers={'content-type':'application/json'}))
   with self.assertRaises(AdminStopped):await c.exchange_code({'code':'synthetic'})
 async def test_encoding_mime_length(self):
  for h in [{'content-type':'text/html'},{'content-type':'application/json','content-encoding':'gzip'},{'content-type':'application/json','content-length':str(MAX_BYTES+1)}]:
   c=self.client(lambda r:httpx.Response(200,stream=Stream(b'{}'),headers=h))
   with self.assertRaises(AdminStopped):await c.exchange_code({'code':'synthetic'})
 async def test_stream_cap(self):
  c=self.client(lambda r:httpx.Response(200,stream=Stream(b'x'*(MAX_BYTES+1)),headers={'content-type':'application/json'}))
  with self.assertRaises(AdminStopped):await c.exchange_code({'code':'synthetic'})
 async def test_timeout(self):
  class Slow(httpx.AsyncByteStream):
   async def __aiter__(self):await asyncio.sleep(1);yield b'{}'
  c=self.client(lambda r:httpx.Response(200,stream=Slow(),headers={'content-type':'application/json'}),total_seconds=0.01)
  with self.assertRaises(AdminStopped):await c.exchange_code({'code':'synthetic'})
 async def test_full_traceback_private(self):
  def fail(request):raise RuntimeError('PRIVATE-ADMIN-CANARY')
  c=self.client(fail)
  body={'code':'SYNTHETIC-CODE'}
  try:await c.exchange_code(body)
  except AdminStopped as error:
   text=''.join(traceback.format_exception(type(error),error,error.__traceback__))
   self.assertNotIn('PRIVATE-ADMIN-'+'CANARY',text);self.assertNotIn('SYNTHETIC-'+'CODE',text)
  else:self.fail('error accepted')
 async def test_import_construction_no_network(self):
  with patch('httpx.AsyncClient',side_effect=AssertionError('HTTP accessed')):AdminAISHTTP(lambda:TOKEN)
 async def test_caller_cancel_propagates(self):
  class Slow(httpx.AsyncByteStream):
   async def __aiter__(self):await asyncio.sleep(10);yield b'{}'
  c=self.client(lambda r:httpx.Response(200,stream=Slow(),headers={'content-type':'application/json'}))
  task=asyncio.create_task(c.exchange_code({'code':'synthetic'}));await asyncio.sleep(0.01);task.cancel()
  with self.assertRaises(asyncio.CancelledError):await task

if __name__=='__main__':unittest.main()
