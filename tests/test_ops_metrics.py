"""Public ops metrics honesty for Agent FinOps."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agent_finops.api.main import app


def test_ops_metrics_exposes_store_and_enforcement_honesty():
    client = TestClient(app)
    resp = client.get("/v1/ops/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "agent-finops"
    extra = body["extra"]
    assert "store_backend" in extra
    assert extra["enforcement"] == "caller_owned"
    assert "auth_required_mutations" in extra


def test_health_exposes_store_backend():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "store_backend" in body


def test_observability_status_meter_vs_enforce():
    client = TestClient(app)
    resp = client.get("/v1/observability/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "source_of_truth" in body
    assert body["planes"]["enforcement"] == "caller_owned"
    assert "store_backend" in body["planes"]
    names = {e["name"] for e in body["exporters"]}
    assert "OpsMetrics" in names
    assert "enforce" in body["recommendation"].lower() or "caller" in body["recommendation"].lower()
