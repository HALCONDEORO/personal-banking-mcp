import unittest
from admin_consent import ConsentAttempt


class TestConsentLifecycle(unittest.TestCase):
    def make_attempt(self):
        self.clock = [100.0]
        return ConsentAttempt('https://localhost:8765/callback', clock=lambda: self.clock[0])

    def test_remaining_uses_monotonic_clock(self):
        attempt = self.make_attempt()
        self.assertFalse(attempt.closed)
        self.assertEqual(attempt.remaining_seconds, 300.0)
        self.clock[0] += 20.5
        self.assertEqual(attempt.remaining_seconds, 279.5)
        self.assertFalse(attempt.closed)

    def test_expiry_is_closed_and_remaining_never_negative(self):
        attempt = self.make_attempt()
        self.clock[0] = 400.0
        self.assertTrue(attempt.closed)
        self.assertEqual(attempt.remaining_seconds, 0.0)
        self.clock[0] = 500.0
        self.assertTrue(attempt.closed)
        self.assertEqual(attempt.remaining_seconds, 0.0)

    def test_cancel_closes_before_deadline(self):
        attempt = self.make_attempt()
        attempt.cancel()
        self.assertTrue(attempt.closed)
        self.assertEqual(attempt.remaining_seconds, 0.0)
        attempt.cancel()
        self.assertTrue(attempt.closed)


if __name__ == '__main__':
    unittest.main()
