"""Explicit portable synthetic suite. Never selects live banking or key setup."""
import sys
import unittest

# Deliberately explicit: new modules need review before joining this Windows gate.
MODULES = (
    'test_server', 'test_review', 'test_invariants_independent',
    'test_fixture_analytics_wiring', 'test_provider_normalize',
    'test_provider_pager', 'test_provider_http', 'test_provider_checked_session',
    'test_provider_session', 'test_provider_session_offsets',
    'test_provider_json_numbers', 'test_provider_load', 'test_provider_doctor',
    'test_provider_provenance', 'test_http_cancellation_cleanup',
    'test_read_composition_cleanup', 'test_queue_cleanup',
    'test_checked_read_http_integration', 'test_checked_read_http_failures',
    'test_transaction_analytics', 'test_transaction_export',
    'test_transaction_recurring', 'test_money_corpus',
    'test_adversarial_corpus', 'test_callback_contract_join',
    'test_callback_framing', 'test_callback_receiver',
    'test_callback_adversarial_corpus', 'test_admin_consent',
    'test_admin_http', 'test_admin_lifecycle', 'test_admin_time_boundary',
)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    # A skipped module is not Windows evidence. Keep discovery errors and an
    # accidentally empty selection red instead of manufacturing a green gate.
    return 0 if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else 1


if __name__ == '__main__':
    sys.exit(main())
