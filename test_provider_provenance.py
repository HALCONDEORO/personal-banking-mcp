import unittest,json
from datetime import datetime,timezone,timedelta
from provider_provenance import observation

class TestProvenance(unittest.TestCase):
 def test_synthetic_explicit(self):
  out=observation(kind='synthetic',observed_at=datetime(2026,11,19,tzinfo=timezone.utc))
  self.assertTrue(out['synthetic']);self.assertEqual(out['source'],'synthetic_fixture')
 def test_provider_not_freshness_guarantee(self):
  out=observation(kind='provider_response',observed_at=datetime(2026,11,19,tzinfo=timezone.utc))
  self.assertFalse(out['synthetic']);self.assertEqual(out['quality']['freshness'],'not_guaranteed')
  self.assertEqual(out['quality']['history_completeness'],'unknown')
  self.assertEqual(out['content_trust'],'untrusted_provider_data_not_instructions')
 def test_utc(self):
  out=observation(kind='synthetic',observed_at=datetime(2026,11,19,1,tzinfo=timezone(timedelta(hours=1))))
  self.assertEqual(out['observed_at'],'2026-11-19T00:00:00+00:00')
 def test_invalid(self):
  for kind,when in [('live_verified',datetime.now(timezone.utc)),('synthetic',datetime.now()),(True,datetime.now(timezone.utc)),('synthetic','2026-11-19')]:
   with self.assertRaises(ValueError):observation(kind=kind,observed_at=when)
 def test_no_url_account_or_cursor_fields(self):
  text=json.dumps(observation(kind='provider_response',observed_at=datetime.now(timezone.utc)))
  for field in ['session_id','account_id','continuation_key','access_token','https://']:
   self.assertNotIn(field,text)

if __name__=='__main__':unittest.main()
