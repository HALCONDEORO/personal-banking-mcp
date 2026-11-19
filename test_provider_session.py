import copy,json,traceback,unittest
from datetime import datetime,timezone,timedelta
from provider_session import validate_created_session,PrivateSession,SessionRejected

NOW=datetime(2026,11,19,19,tzinfo=timezone.utc)
UNTIL=NOW+timedelta(hours=1)
SID='11111111-1111-4111-8111-111111111111'
AID='22222222-2222-4222-8222-222222222222'

class TestSession(unittest.TestCase):
 def setUp(self):
  self.p={'session_id':SID,'accounts':[{'uid':AID,'account_id':{'iban':'SYNTHETIC-PRIVATE-IBAN'},'name':'PRIVATE NAME'}],
          'aspsp':{'name':'Selected synthetic bank','country':'IE'},'psu_type':'personal',
          'access':{'valid_until':UNTIL.isoformat()}}
 def check(self,p=None,**extra):
  return validate_created_session(p if p is not None else self.p,selected_bank='Selected synthetic bank',selected_country='IE',requested_until=extra.get('until',UNTIL),now=extra.get('now',NOW))
 def test_minimal_private_ids(self):
  s=self.check();self.assertEqual(s.transport_ids(now=NOW),(SID,(AID,)))
  text=json.dumps(s.summary(now=NOW))+repr(s)
  for private in [SID,AID,'SYNTHETIC-PRIVATE-IBAN','PRIVATE NAME']:self.assertNotIn(private,text)
  self.assertEqual(s.summary(now=NOW)['live_consent_status'],'not_verified')
 def test_expiry_at_boundary(self):
  s=self.check()
  with self.assertRaises(SessionRejected):s.transport_ids(now=UNTIL)
  with self.assertRaises(SessionRejected):self.check(now=UNTIL)
 def test_provider_cannot_extend(self):
  with self.assertRaises(SessionRejected):self.check(until=UNTIL-timedelta(seconds=1))
 def test_personal_only(self):
  for value in ['business',None,True]:
   self.p['psu_type']=value
   with self.assertRaises(SessionRejected):self.check()
 def test_bank_binding(self):
  for k,v in [('name','Other bank'),('country','GB')]:
   p=copy.deepcopy(self.p);p['aspsp'][k]=v
   with self.assertRaises(SessionRejected):self.check(p)
 def test_no_accounts(self):
  for value in [[],None,{},[{}],[AID]]:
   self.p['accounts']=value
   with self.assertRaises(SessionRejected):self.check()
 def test_duplicates(self):
  self.p['accounts']*=2
  with self.assertRaises(SessionRejected):self.check()
 def test_maximum_accounts(self):
  self.p['accounts']=[{'uid':f'{i:08x}-1111-4111-8111-111111111111'} for i in range(1,52)]
  with self.assertRaises(SessionRejected):self.check()
 def test_uuid_strict(self):
  for value in [True,123,None,'00000000-0000-0000-0000-000000000000','../../sessions','{'+SID+'}',SID.replace('-','')]:
   self.p['session_id']=value
   with self.subTest(value=value),self.assertRaises(SessionRejected):self.check()
 def test_time_strict(self):
  for value in ['2026-11-19','2026-11-19T20:00:00','2026-99-19T20:00:00Z','2026-11-19T20:00:00Z\n',None]:
   self.p['access']['valid_until']=value
   with self.subTest(value=value),self.assertRaises(SessionRejected):self.check()
 def test_no_naive_clock(self):
  with self.assertRaises(SessionRejected):self.check(now=NOW.replace(tzinfo=None))
 def test_shorter_access_allowed(self):
  self.p['access']['valid_until']=(UNTIL-timedelta(minutes=30)).isoformat()
  self.assertEqual(self.check().summary(now=NOW)['account_count'],1)
 def test_extra_data_dropped(self):
  self.p['password']='PRIVATE EXTRA';s=self.check()
  self.assertFalse(hasattr(s,'__dict__'));self.assertFalse(hasattr(s,'password'))
 def test_full_traceback_generic(self):
  candidate=copy.deepcopy(self.p);candidate['access']['valid_until']='PRIVATE-EXPIRY-CANARY'
  try:self.check(candidate)
  except SessionRejected as error:
   text=''.join(traceback.format_exception(type(error),error,error.__traceback__))
   self.assertNotIn('PRIVATE-EXPIRY-'+'CANARY',text)
   self.assertNotIn(SID,text)
  else:self.fail('invalid accepted')
 def test_constructor_validates(self):
  for accounts in [(None,),([],),(),(AID,AID)]:
   with self.assertRaises(SessionRejected):PrivateSession(SID,accounts,UNTIL)
 def test_input_not_changed(self):
  before=copy.deepcopy(self.p);self.check();self.assertEqual(before,self.p)

if __name__=='__main__':unittest.main()
