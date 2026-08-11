"""Stripe Billing Meters (test mode) — commercial mirror of FinOps usage. No live charges."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class MeterEvent:
    tenant_id: str
    customer_id: str
    event_name: str
    value: float
    recorded_at: str
    stripe_mode: str = "test"


@dataclass
class StripeMeterReporter:
    """Records usage meter events locally + optionally posts to Stripe test API."""

    events: list[MeterEvent] = field(default_factory=list)

    def enabled(self) -> bool:
        return bool(os.getenv("STRIPE_API_KEY", "").strip()) or os.getenv(
            "STRIPE_METER_LOCAL", "true"
        ).lower() in {"1", "true", "yes"}

    def test_mode_only(self) -> bool:
        key = os.getenv("STRIPE_API_KEY", "")
        return not key or key.startswith("sk_test")

    def customer_id_for_tenant(self, tenant_id: str) -> str:
        mapping = os.getenv("STRIPE_TENANT_CUSTOMER_MAP", "")
        # format: acme:cus_xxx,other:cus_yyy
        for part in mapping.split(","):
            if ":" not in part:
                continue
            tid, cid = part.split(":", 1)
            if tid.strip() == tenant_id:
                return cid.strip()
        return f"cus_test_{tenant_id}"

    def record_usage_meter(
        self,
        *,
        tenant_id: str,
        value: float,
        event_name: str | None = None,
    ) -> dict[str, Any]:
        if not self.test_mode_only():
            raise RuntimeError("Live Stripe keys refused — test mode only for Acme embed.")
        name = event_name or os.getenv("STRIPE_METER_EVENT_NAME", "acme_llm_cost_millicents")
        customer_id = self.customer_id_for_tenant(tenant_id)
        event = MeterEvent(
            tenant_id=tenant_id,
            customer_id=customer_id,
            event_name=name,
            value=value,
            recorded_at=datetime.now(UTC).isoformat(),
            stripe_mode="test",
        )
        self.events.append(event)

        stripe_posted = False
        stripe_error: str | None = None
        api_key = os.getenv("STRIPE_API_KEY", "").strip()
        if api_key:
            try:
                import httpx

                with httpx.Client(timeout=15) as client:
                    response = client.post(
                        "https://api.stripe.com/v1/billing/meter_events",
                        auth=(api_key, ""),
                        data={
                            "event_name": name,
                            "payload[stripe_customer_id]": customer_id,
                            "payload[value]": str(int(value)),
                        },
                    )
                    response.raise_for_status()
                    stripe_posted = True
            except Exception as exc:  # noqa: BLE001
                stripe_error = str(exc)

        return {
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "event_name": name,
            "value": value,
            "stripe_mode": "test",
            "stripe_posted": stripe_posted,
            "stripe_error": stripe_error,
            "local_only": not stripe_posted,
            "recorded_at": event.recorded_at,
        }

    def invoice_preview(self, tenant_id: str) -> dict[str, Any]:
        rows = [e for e in self.events if e.tenant_id == tenant_id]
        total = sum(e.value for e in rows)
        # millicents → USD if using cost millicents meter
        usd = total / 100_000.0 if total > 1000 else total
        return {
            "tenant_id": tenant_id,
            "stripe_mode": "test",
            "line_items": [
                {
                    "customer_id": e.customer_id,
                    "event_name": e.event_name,
                    "value": e.value,
                    "recorded_at": e.recorded_at,
                }
                for e in rows
            ],
            "usage_total": total,
            "estimated_invoice_usd": round(usd, 4),
            "honesty": "Stripe test-mode invoice preview — no live charges.",
        }


_reporter = StripeMeterReporter()


def get_stripe_meter_reporter() -> StripeMeterReporter:
    return _reporter
