import asyncio,unittest
from datetime import datetime,timezone
from urllib.parse import urlencode
from callback_receiver import CallbackReceiver,ReceiverStopped
from callback_framing import relay_request
from admin_consent import ConsentAttempt

class TestReceiver(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.attempt=ConsentAttempt('https://localhost:8765/callback')
  body=self.attempt.authorization_body('Synthetic bank','IE',now=datetime.now(timezone.utc))
  self.target='/callback?'+urlencode({'state':body['state'],'code':'SYNTHETIC-PRIVATE-CODE'})
  self.receiver=CallbackReceiver(self.attempt,port=0,read_seconds=0.05,lifetime_seconds=0.4)
  await self.receiver.start();self.port=self.receiver.port
 async def asyncTearDown(self):await self.receiver.close()
 async def request(self,raw):
  reader,writer=await asyncio.open_connection('127.0.0.1',self.port)
  writer.write(raw);await writer.drain();writer.write_eof()
  response=await asyncio.wait_for(reader.read(),1)
  writer.close();await writer.wait_closed()
  return response
 async def test_socket_success_private_and_closes(self):
  waiter=asyncio.create_task(self.receiver.wait_private_result())
  response=await self.request(relay_request(self.target))
  result=await asyncio.wait_for(waiter,1)
  self.assertEqual(result,{'code':'SYNTHETIC-PRIVATE-CODE'})
  self.assertNotIn(result['code'].encode(),response);self.assertIn(b'not confirmed',response)
  with self.assertRaises(OSError):await asyncio.open_connection('127.0.0.1',self.port)
 async def test_bad_then_good(self):
  response=await self.request(b'malformed synthetic request')
  self.assertIn(b'400 Bad Request',response)
  waiter=asyncio.create_task(self.receiver.wait_private_result())
  await self.request(relay_request(self.target));await asyncio.wait_for(waiter,1)
 async def test_trailing_body_rejected(self):
  response=await self.request(relay_request(self.target)+b'body')
  self.assertIn(b'400 Bad Request',response)
 async def test_pipeline_rejected(self):
  response=await self.request(relay_request(self.target)*2)
  self.assertIn(b'400 Bad Request',response)
 async def test_read_timeout(self):
  reader,writer=await asyncio.open_connection('127.0.0.1',self.port)
  writer.write(b'GET ');await writer.drain()
  response=await asyncio.wait_for(reader.read(),1)
  self.assertIn(b'400 Bad Request',response)
  writer.close();await writer.wait_closed()
 async def test_expiry_without_wait_call(self):
  await asyncio.sleep(0.45)
  self.assertTrue(self.attempt.closed)
  with self.assertRaises(OSError):await asyncio.open_connection('127.0.0.1',self.port)
 async def test_wait_expiry_generic(self):
  with self.assertRaisesRegex(ReceiverStopped,'^Callback receiver stopped$'):
   await self.receiver.wait_private_result()
 async def test_attempt_expires_during_callback(self):
  self.attempt.cancel()
  response=await self.request(relay_request(self.target))
  self.assertIn(b'400 Bad Request',response)
  with self.assertRaises(OSError):await asyncio.open_connection('127.0.0.1',self.port)
 async def test_connection_budget(self):
  for _ in range(8):await self.request(b'invalid')
  with self.assertRaises(OSError):await asyncio.open_connection('127.0.0.1',self.port)
 async def test_oversize(self):
  response=await self.request(b'x'*12300)
  self.assertIn(b'400 Bad Request',response)
 async def test_exact_loopback_bind(self):
  self.assertEqual(self.receiver._server.sockets[0].getsockname()[0],'127.0.0.1')
 async def test_no_restart(self):
  with self.assertRaises(ReceiverStopped):await self.receiver.start()
 async def test_private_repr(self):self.assertEqual(repr(self.receiver),'<CallbackReceiver private>')
 async def test_invalid_configuration(self):
  for values in [{'port':True},{'port':-1},{'port':65536},{'read_seconds':True},{'read_seconds':3},{'lifetime_seconds':float('nan')}]:
   with self.subTest(values=values),self.assertRaises(ReceiverStopped):CallbackReceiver(self.attempt,**values)

if __name__=='__main__':unittest.main()
