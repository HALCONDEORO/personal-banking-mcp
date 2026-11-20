# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Actual Python framing + actual consent validation, in memory only.

No sockets, TLS, relay implementation, signer, C#, Windows, store, HTTP provider
or bank connection. These tests check layering and return values, not the
missing local-process authentication or full logging/memory behavior.
"""
import unittest
from datetime import datetime, timezone
from urllib.parse import urlencode
from admin_consent import ConsentAttempt, SetupRejected
from callback_framing import (ORIGIN, MAX_TARGET, relay_request,
                              parse_relay_request, response_bytes)


class CallbackJoinTests(unittest.TestCase):
    def make_attempt(self):
        self.clock = [0.0]
        attempt = ConsentAttempt(ORIGIN + '/callback', clock=lambda: self.clock[0])
        body = attempt.authorization_body('Synthetic selected bank', 'IE',
                                           now=datetime(2026, 11, 20, tzinfo=timezone.utc))
        return attempt, body['state']

    def joined(self, attempt, query):
        return attempt.consume_callback(parse_relay_request(
            relay_request('/callback?' + urlencode(query))))

    def test_positive_private_code_and_constant_response_are_separate_outputs(self):
        attempt, state = self.make_attempt()
        query = {'state': state, 'code': 'SYNTHETIC-PRIVATE-CODE'}
        self.assertEqual(self.joined(attempt, query), {'code': 'SYNTHETIC-PRIVATE-CODE'})
        response = response_bytes(accepted=True)
        self.assertIn(b'200 OK', response)
        self.assertIn(b'Bank session is not confirmed', response)
        self.assertNotIn(state.encode(), response)
        self.assertNotIn(query['code'].encode(), response)
        with self.assertRaises(SetupRejected):
            self.joined(attempt, query)

    def test_wrong_state_does_not_burn_valid_joined_attempt(self):
        attempt, state = self.make_attempt()
        with self.assertRaises(SetupRejected):
            self.joined(attempt, {'state': 'wrong', 'code': 'synthetic'})
        self.assertFalse(attempt.closed)
        self.assertEqual(self.joined(attempt, {'state': state, 'code': 'synthetic'}),
                         {'code': 'synthetic'})

    def test_matching_state_denial_consumes_attempt_and_never_returns_description(self):
        attempt, state = self.make_attempt()
        with self.assertRaises(SetupRejected) as error:
            self.joined(attempt, {'state': state, 'error': 'access_denied',
                                 'error_description': 'SYNTHETIC-PRIVATE-DESCRIPTION'})
        self.assertEqual(str(error.exception), 'Setup request rejected')
        self.assertTrue(attempt.closed)
        with self.assertRaises(SetupRejected):
            self.joined(attempt, {'state': state, 'code': 'synthetic'})
        self.assertNotIn(b'SYNTHETIC-PRIVATE-DESCRIPTION', response_bytes(accepted=False))

    def test_syntactically_valid_framing_is_not_valid_consent(self):
        for encoded in ['code=one&code=two', 'code=%00', 'code=%FF', 'code=synthetic&unknown=x']:
            attempt, state = self.make_attempt()
            target = '/callback?state=' + state + '&' + encoded
            private_url = parse_relay_request(relay_request(target))
            self.assertEqual(private_url, ORIGIN + target)
            with self.subTest(encoded=encoded), self.assertRaises(SetupRejected):
                attempt.consume_callback(private_url)

    def test_framing_target_limit_is_not_the_full_url_limit(self):
        attempt, _ = self.make_attempt()
        target = '/callback?x=' + 'x' * (MAX_TARGET - len('/callback?x='))
        private_url = parse_relay_request(relay_request(target))
        self.assertEqual(len(target), 8192)
        self.assertGreater(len(private_url), 8192)
        with self.assertRaises(SetupRejected):
            attempt.consume_callback(private_url)

    def test_joined_callback_cannot_extend_monotonic_ttl(self):
        attempt, state = self.make_attempt()
        target = '/callback?' + urlencode({'state': state, 'code': 'synthetic'})
        private_url = parse_relay_request(relay_request(target))
        self.clock[0] = 300.0
        with self.assertRaises(SetupRejected):
            attempt.consume_callback(private_url)
        self.assertTrue(attempt.closed)


if __name__ == '__main__':
    unittest.main()
