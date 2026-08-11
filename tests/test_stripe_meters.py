"""Tests for Stripe test-mode meters (Acme embed P10)."""

from __future__ import annotations

import unittest

from agent_finops.stripe_meters import StripeMeterReporter


class StripeMeterTests(unittest.TestCase):
    def test_invoice_preview_local(self) -> None:
        reporter = StripeMeterReporter()
        reporter.record_usage_meter(tenant_id="acme", value=1500)
        reporter.record_usage_meter(tenant_id="acme", value=500)
        preview = reporter.invoice_preview("acme")
        self.assertEqual(preview["usage_total"], 2000)
        self.assertEqual(preview["stripe_mode"], "test")
        self.assertIn("honesty", preview)

    def test_refuses_live_keys(self) -> None:
        import os

        reporter = StripeMeterReporter()
        old = os.environ.get("STRIPE_API_KEY")
        os.environ["STRIPE_API_KEY"] = "sk_live_fake"
        try:
            with self.assertRaises(RuntimeError):
                reporter.record_usage_meter(tenant_id="acme", value=1)
        finally:
            if old is None:
                os.environ.pop("STRIPE_API_KEY", None)
            else:
                os.environ["STRIPE_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()
