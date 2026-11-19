import unittest
import traceback
from datetime import datetime, timezone
from urllib.parse import urlencode
from admin_consent import ConsentAttempt, SetupRejected

R = 'https://localhost:8765/callback'
NOW = datetime(2026, 11, 19, tzinfo=timezone.utc)

class TestConsent(unittest.TestCase):
    def setUp(self):
        self.time = [100.0]
        self.a = ConsentAttempt(R, clock=lambda:self.time[0])
        self.body = self.a.authorization_body('Selected test bank', 'IE', now=NOW)
        self.state = self.body['state']
    def callback(self, **extra):
        return R+'?'+urlencode({'state':self.state, **extra})
    def test_shape(self):
        self.assertEqual(self.body['psu_type'], 'personal')
        self.assertEqual(self.body['redirect_url'], R)
        self.assertEqual(self.body['access']['valid_until'], '2026-11-19T01:00:00+00:00')
        self.assertGreaterEqual(len(self.state), 43)
    def test_unique(self):
        b=ConsentAttempt(R).authorization_body('Test', 'IE', now=NOW)
        self.assertNotEqual(self.state,b['state'])
    def test_one_use(self):
        self.assertEqual(self.a.consume_callback(self.callback(code='synthetic-code')), {'code':'synthetic-code'})
        with self.assertRaises(SetupRejected):self.a.consume_callback(self.callback(code='again'))
    def test_expiry(self):
        self.time[0]=400
        with self.assertRaises(SetupRejected):self.a.consume_callback(self.callback(code='x'))
    def test_cancel(self):
        self.a.cancel()
        with self.assertRaises(SetupRejected):self.a.authorization_body('Test','IE',now=NOW)
    def test_invalid_state_not_consume(self):
        with self.assertRaises(SetupRejected):self.a.consume_callback(R+'?state=wrong&code=x')
        self.assertEqual(self.a.consume_callback(self.callback(code='good')),{'code':'good'})
    def test_error_consumes_generic(self):
        with self.assertRaises(SetupRejected) as e:self.a.consume_callback(self.callback(error='denied',error_description='private-test-error'))
        self.assertNotIn('private-test-error',str(e.exception))
        with self.assertRaises(SetupRejected):self.a.consume_callback(self.callback(code='x'))
    def test_full_traceback_does_not_leak(self):
        candidate=R+'?state='+self.state+'&PRIVATE-CODE-CANARY'
        try:
            self.a.consume_callback(candidate)
        except SetupRejected as error:
            text=''.join(traceback.format_exception(type(error),error,error.__traceback__))
            self.assertNotIn('PRIVATE-CODE-'+'CANARY',text)
            self.assertNotIn(self.state,text)
        else:self.fail('malformed callback accepted')
    def test_duplicate_params(self):
        with self.assertRaises(SetupRejected):self.a.consume_callback(self.callback(code='x')+'&code=y')
    def test_unknown_param(self):
        with self.assertRaises(SetupRejected):self.a.consume_callback(self.callback(code='x',next='elsewhere'))
    def test_conflicting_error(self):
        with self.assertRaises(SetupRejected):self.a.consume_callback(self.callback(code='x',error='no'))
    def test_origin(self):
        for bad in ['http://localhost:8765/callback','https://evil.test/callback','https://localhost:8765@evil.test/callback',R+'#fragment']:
            with self.subTest(bad=bad),self.assertRaises(SetupRejected):self.a.consume_callback(bad+'?'+urlencode({'state':self.state,'code':'x'}))
    def test_bad_encoding(self):
        for code in ['%zz','%FF','%00','%20','%7f']:
            with self.subTest(code=code),self.assertRaises(SetupRejected):self.a.consume_callback(R+'?state='+self.state+'&code='+code)
            # A matched state may burn attempt on malformed code, so renew.
            self.setUp()
    def test_bounds(self):
        with self.assertRaises(SetupRejected):self.a.consume_callback(self.callback(code='x'*9000))
    def test_empty(self):
        with self.assertRaises(SetupRejected):self.a.consume_callback(self.callback(code=''))
    def test_private_repr(self):
        self.assertNotIn(self.state,repr(self.a))
    def test_config_types(self):
        for ttl in [True,0,301,3.0,'60']:
            with self.subTest(ttl=ttl),self.assertRaises(SetupRejected):ConsentAttempt(R,ttl_seconds=ttl)
        for url in ['http://localhost:8765/callback','https://localhost/callback',R+'?x=1']:
            with self.assertRaises(SetupRejected):ConsentAttempt(url)
    def test_bank_required(self):
        for name,country in [('', 'IE'),('Test','ie'),('Test\n','IE')]:
            with self.assertRaises(SetupRejected):self.a.authorization_body(name,country,now=NOW)
    def test_timezone_required(self):
        with self.assertRaises(SetupRejected):self.a.authorization_body('Test','IE',now=datetime(2026,11,19))
    def test_session_lifetime_bound(self):
        for value in [True,0,86401]:
            with self.assertRaises(SetupRejected):self.a.authorization_body('Test','IE',now=NOW,access_seconds=value)

if __name__=='__main__':unittest.main()
