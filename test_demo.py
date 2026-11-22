"""Tests for the fixture-only walkthrough and its offline report."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import demo


class DemoTests(unittest.TestCase):
    def test_real_protocol_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "demo.html"
            run = subprocess.run([sys.executable, str(demo.ROOT / "demo.py"), "--html", str(report)],
                                 capture_output=True, text=True, timeout=30, cwd=directory)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("Unsupported make_payment tool: REJECTED", run.stdout)
            self.assertIn('"amount": "1234.56"', run.stdout)
            text = report.read_text()
            self.assertIn("2026-01-05", text)
            self.assertNotIn("<script", text)
            self.assertNotIn("src=", text)
            self.assertNotIn("http://", text)
            self.assertNotIn("https://", text)
            original = report.read_bytes()
            second = subprocess.run([sys.executable, str(demo.ROOT / "demo.py"), "--html", str(report)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(second.returncode, 1)
            self.assertEqual(report.read_bytes(), original)
            self.assertNotIn("Traceback", second.stderr)

    def test_untrusted_text_is_escaped(self):
        report = {"steps": [{"tool": "<img src=x>", "result": {"description": "</pre><script>alert(1)</script>"}}]}
        rendered = demo.render_html(report)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img src=x>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_failure_does_not_echo_diagnostics(self):
        with patch("demo.asyncio.run", side_effect=RuntimeError("private-canary")), \
                patch("demo.walkthrough", new=lambda: None), \
                patch("sys.stderr") as stderr:
            self.assertEqual(demo.main([]), 1)
        self.assertNotIn("private-canary", str(stderr.write.call_args_list))


if __name__ == "__main__":
    unittest.main()
