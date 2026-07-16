from agent_finops_client.client import FinOpsClient


def test_record_outcome_offline():
    c = FinOpsClient(base_url=None)
    out = c.record_outcome(
        workflow_id="w1",
        tenant_id="omniforge",
        eval_pass=True,
        total_cost_usd=0.2,
    )
    assert out["compliant_success"] is True
    assert out["offline"] is True


def test_kpi_offline():
    c = FinOpsClient(base_url=None)
    k = c.get_cost_per_compliant_outcome("vap")
    assert k["cost_per_compliant_outcome"] is None
    assert k["offline"] is True
