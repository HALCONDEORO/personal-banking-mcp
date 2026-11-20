"""Independent offline corpus runner. Never opens a real connection.
Run with unittest discovery or python -m unittest test_adversarial_corpus.
Only reads target source and uses injected httpx.MockTransport.
"""
import asyncio,copy,json,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import urlencode
import admin_consent as consent
import provider_session as session
import provider_pager as pager
import provider_http as http
import httpx
CORPUS=json.loads((Path(__file__).parent/'fuzz-corpus'/'banking-session-reads.json').read_text())
NOW=datetime(2026,11,20,6,tzinfo=timezone.utc);UNTIL=NOW+timedelta(hours=1)
SID='11111111-1111-4111-8111-111111111111';AID='22222222-2222-4222-8222-222222222222';OTHER='33333333-3333-4333-8333-333333333333'
R='https://localhost:8765/callback'
class Corpus(unittest.IsolatedAsyncioTestCase):
 def test_corpus_manifest(self):
  self.assertEqual(CORPUS['schema_version'],1)
  cases=CORPUS['cases']
  self.assertEqual(len(cases),77)
  self.assertEqual(len({case['id'] for case in cases}),77)
  allowed={'session','consent','read_denied','status','consent_positive','session_positive','read_positive','cancel','lifecycle','cursor'}
  self.assertTrue(all(case['kind'] in allowed for case in cases))
 async def test_corpus(self):
  for case in CORPUS['cases']:
   with self.subTest(case=case['id']):await self.run_case(case)
 async def run_case(self,c):
  kind=c['kind']
  if kind=='session':
   p={'session_id':SID,'accounts':[{'uid':AID}], 'aspsp':{'name':'Synthetic bank','country':'IE'},'psu_type':'personal','access':{'valid_until':UNTIL.isoformat()}}
   ref=p
   for key in c['path'][:-1]:ref=ref[key]
   ref[c['path'][-1]]=c['value']
   with self.assertRaises(session.SessionRejected) as err:session.validate_created_session(p,selected_bank='Synthetic bank',selected_country='IE',requested_until=UNTIL,now=NOW)
   self.assertEqual(str(err.exception),'Session validation rejected')
  elif kind=='consent':
   clock=[0.0];a=consent.ConsentAttempt(R,clock=lambda:clock[0]);body=a.authorization_body('Synthetic bank','IE',now=NOW)
   if c.get('advance') is not None:clock[0]=c['advance']
   query={'state':body['state'],'code':'synthetic-code'};query.update(c.get('params',{}));url=c.get('origin',R)+'?'+urlencode(query)+c.get('suffix','')
   with self.assertRaises(consent.SetupRejected) as err:a.consume_callback(url)
   self.assertEqual(str(err.exception),'Setup request rejected')
   if c.get('burns'):
    with self.assertRaises(consent.SetupRejected):a.consume_callback(R+'?'+urlencode({'state':body['state'],'code':'second'}))
  elif kind=='read_denied':
   counters={'token':0,'http':0}
   def token():counters['token']+=1;return 'abc.def.ghi'
   async def handler(req):counters['http']+=1;raise AssertionError('denied input reached transport')
   client=http.ReadOnlyHTTP(token,accounts=frozenset([AID]),session=SID,_test_transport=httpx.MockTransport(handler))
   req=pager.ReadRequest(c.get('host',pager.HOST),c.get('path','/accounts/'+AID+'/transactions'),tuple(tuple(x) for x in c.get('query',[])))
   with self.assertRaises(pager.FetchStopped):await client(req)
   self.assertEqual(counters,{'token':0,'http':0})
  elif kind=='status':
   calls=[]
   async def fake(req):calls.append(req);return pager.FakeResponse(c['status'],b'SYNTHETIC-PRIVATE-BODY')
   with self.assertRaisesRegex(pager.FetchStopped,'^'+c['expected']+'$'):
    await pager.fetch_simulated_transactions(AID,frozenset([AID]),'2026-01-01','2026-01-02',fake)
   self.assertEqual(len(calls),1)
  elif kind=='consent_positive':
   a=consent.ConsentAttempt(R);body=a.authorization_body('Synthetic bank','IE',now=NOW)
   if c.get('wrong_first'):
    with self.assertRaises(consent.SetupRejected):a.consume_callback(R+'?state=wrong&code=synthetic')
   url=R+'?'+urlencode({'state':body['state'],'code':'synthetic-code'})
   self.assertEqual(a.consume_callback(url),{'code':'synthetic-code'})
   with self.assertRaises(consent.SetupRejected):a.consume_callback(url)
  elif kind=='session_positive':
   p={'session_id':SID,'accounts':[{'uid':AID,'name':'SYNTHETIC-PRIVATE-NAME'}], 'aspsp':{'name':'Synthetic bank','country':'IE'},'psu_type':'personal','access':{'valid_until':UNTIL.isoformat()}}
   before=copy.deepcopy(p);result=session.validate_created_session(p,selected_bank='Synthetic bank',selected_country='IE',requested_until=UNTIL,now=NOW)
   self.assertEqual(p,before);self.assertEqual(result.transport_ids(now=NOW),(SID,(AID,)))
   summary=json.dumps(result.summary(now=NOW));self.assertNotIn(AID,summary);self.assertNotIn(SID,summary);self.assertNotIn('SYNTHETIC-PRIVATE-NAME',summary)
   self.assertEqual(result.summary(now=NOW)['live_consent_status'],'not_verified')
  elif kind=='read_positive':
   calls=[]
   async def handler(req):
    calls.append(req);return httpx.Response(200,headers={'content-type':'application/json'},stream=httpx.ByteStream(b'{}'))
   client=http.ReadOnlyHTTP(lambda:'abc.def.ghi',accounts=frozenset([AID]),session=SID,_test_transport=httpx.MockTransport(handler))
   req=pager.ReadRequest(pager.HOST,'/accounts/'+AID+'/balances',())
   result=await client(req);self.assertEqual(result.body,b'{}');self.assertEqual(len(calls),1);self.assertEqual(calls[0].method,'GET')
  elif kind=='cancel':
   called=asyncio.Event();cancelled=[]
   async def fake(req):
    called.set()
    try:await asyncio.Event().wait()
    finally:cancelled.append(True)
   task=asyncio.create_task(pager.fetch_simulated_transactions(AID,frozenset([AID]),'2026-01-01','2026-01-02',fake))
   await called.wait();task.cancel()
   with self.assertRaises(asyncio.CancelledError):await task
   self.assertEqual(cancelled,[True])
  elif kind=='lifecycle':
   p=session.PrivateSession(SID,(AID,),UNTIL)
   with self.assertRaises(session.SessionRejected):p.transport_ids(now=UNTIL)
   self.assertEqual(p.summary(now=NOW)['live_consent_status'],'not_verified')
   self.assertNotIn(AID,repr(p));self.assertNotIn(SID,repr(p))
  elif kind=='cursor':
   calls=[]
   async def fake(req):
    calls.append(req);return pager.FakeResponse(200,json.dumps({'transactions':[],'continuation_key':c['value'] if len(calls)==1 else None}).encode())
   result=await pager.fetch_simulated_transactions(AID,frozenset([AID]),'2026-01-01','2026-01-02',fake)
   self.assertEqual(len(calls),2);self.assertEqual(calls[1].host,pager.HOST);self.assertEqual(calls[1].path,'/accounts/'+AID+'/transactions')
   self.assertEqual(dict(calls[1].query)['continuation_key'],c['value']);self.assertFalse(result['live']);self.assertFalse(result['history_complete'])
  else:raise AssertionError('Unknown corpus kind')
if __name__=='__main__':unittest.main(verbosity=2)
