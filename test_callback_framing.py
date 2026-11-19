import random,unittest,traceback
from datetime import datetime,timezone
from urllib.parse import urlencode
from callback_framing import CallbackRejected,parse_relay_request,relay_request,response_bytes,MAX_REQUEST
from admin_consent import ConsentAttempt,SetupRejected

class TestFraming(unittest.TestCase):
 def test_roundtrip(self):
  target='/callback?state=synthetic&code=synthetic'
  self.assertEqual(parse_relay_request(relay_request(target)),'https://localhost:8765'+target)
 def test_methods(self):
  for method in ['POST','CONNECT','HEAD','OPTIONS','get']:
   with self.subTest(method=method),self.assertRaises(CallbackRejected):parse_relay_request(relay_request('/callback?x=1').replace(b'GET',method.encode(),1))
 def test_host(self):
  for host in ['evil.test','localhost:8765','127.0.0.1:8767','127.0.0.1:8766@evil.test']:
   with self.assertRaises(CallbackRejected):parse_relay_request(relay_request('/callback?x=1').replace(b'127.0.0.1:8766',host.encode()))
 def test_headers(self):
  for header in [b'Content-Length: 0',b'Transfer-Encoding: chunked',b'Host: 127.0.0.1:8766',b'X-Forwarded-Host: evil.test',b'Authorization: PRIVATE']:
   raw=relay_request('/callback?x=1')[:-2]+header+b'\r\n\r\n'
   with self.subTest(header=header),self.assertRaises(CallbackRejected):parse_relay_request(raw)
 def test_targets(self):
  for target in ['https://localhost:8765/callback?x=1','//evil.test/callback?x=1','/callback','/callback/../x?x=1','/callback?x=1#x','/callback?x=1\\x','/callback?x=%xx','/callback?x=\r\nHost: evil','/callback?x=hello world']:
   with self.subTest(target=target),self.assertRaises(CallbackRejected):relay_request(target)
 def test_body_and_pipeline(self):
  raw=relay_request('/callback?x=1')
  for extra in [b'x',raw,b'0\r\n\r\n']:
   with self.assertRaises(CallbackRejected):parse_relay_request(raw+extra)
 def test_encoding_and_type(self):
  for raw in [True,None,'GET',b'\xff\r\n\r\n',b'GET /callback?x=1 HTTP/1.1\nHost: 127.0.0.1:8766\n\n']:
   with self.assertRaises(CallbackRejected):parse_relay_request(raw)
 def test_size(self):
  with self.assertRaises(CallbackRejected):parse_relay_request(b'x'*(MAX_REQUEST+1))
  with self.assertRaises(CallbackRejected):relay_request('/callback?x='+'x'*8192)
 def test_constant_response(self):
  for accepted in [True,False]:
   response=response_bytes(accepted=accepted)
   headers,body=response.split(b'\r\n\r\n',1)
   self.assertIn(b'Cache-Control: no-store',headers);self.assertIn(b'Referrer-Policy: no-referrer',headers)
   self.assertIn(b'Content-Length: '+str(len(body)).encode(),headers)
   self.assertNotIn(b'https://',body)
  self.assertIn(b'not confirmed',response_bytes(accepted=True))
 def test_full_traceback_generic(self):
  candidate=b'PRIVATE-CALLBACK-CANARY'
  try:parse_relay_request(candidate)
  except CallbackRejected as error:
   text=''.join(traceback.format_exception(type(error),error,error.__traceback__))
   self.assertNotIn('PRIVATE-CALLBACK-'+'CANARY',text)
  else:self.fail('invalid accepted')
 def test_seeded_fuzz_has_only_public_error(self):
  rng=random.Random(20261119)
  for _ in range(2000):
   raw=bytes(rng.randrange(256) for _ in range(rng.randrange(150)))
   try:parse_relay_request(raw)
   except CallbackRejected as error:self.assertEqual(str(error),'Callback request rejected')
   else:self.fail('random request unexpectedly accepted')
 def test_private_end_to_end_protocol(self):
  a=ConsentAttempt('https://localhost:8765/callback')
  body=a.authorization_body('Synthetic selected bank','IE',now=datetime.now(timezone.utc))
  target='/callback?'+urlencode({'state':body['state'],'code':'SYNTHETIC-PRIVATE-CODE'})
  url=parse_relay_request(relay_request(target))
  private=a.consume_callback(url)
  self.assertEqual(private,{'code':'SYNTHETIC-PRIVATE-CODE'})
  response=response_bytes(accepted=True)
  self.assertNotIn(body['state'].encode(),response)
  self.assertNotIn(private['code'].encode(),response)
  with self.assertRaises(SetupRejected):a.consume_callback(url)

if __name__=='__main__':unittest.main()
