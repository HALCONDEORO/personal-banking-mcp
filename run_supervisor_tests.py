"""Linux synthetic lifecycle gate, separate from Windows/process qualification."""
from pathlib import Path
import sys
import unittest


def main():
    root = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(
        str(root / 'windows-tls-relay'), pattern='test_relay_supervisor.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    # The reviewed suite has seven socket-backed and five fault-injected tests.
    # A missing/partial discovery or any skipped test must keep the gate red.
    return 0 if (result.wasSuccessful() and result.testsRun >= 12
                 and not result.skipped) else 1


if __name__ == '__main__':
    sys.exit(main())
