from unittest.mock import MagicMock, patch

from agent_finops_client import FinOpsClient


def test_degrades_gracefully_when_no_base_url_configured():
    client = FinOpsClient(base_url=None)
    result = client.record_usage(
        scope_type="agent",
        scope_value="agent-1",
        provider="openai",
        model="gpt-4o-mini",
        prompt_tokens=1_000_000,
        completion_tokens=0,
    )
    assert result.cost_usd == 0.15
    assert result.breached is False


def test_record_usage_posts_to_configured_service():
    client = FinOpsClient(base_url="https://finops.example", api_key="k")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "cost_usd": 0.15,
        "total_cost_usd": 1.5,
        "budget_usd": 5.0,
        "breached": False,
    }
    mock_response.raise_for_status = lambda: None

    with patch("httpx.Client") as mock_httpx:
        mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response
        result = client.record_usage(
            scope_type="agent",
            scope_value="agent-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=1_000_000,
            completion_tokens=0,
        )

    assert result.total_cost_usd == 1.5
    assert result.breached is False


def test_record_usage_sends_api_key_header():
    client = FinOpsClient(base_url="https://finops.example", api_key="secret-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "cost_usd": 0.0,
        "total_cost_usd": 0.0,
        "budget_usd": None,
        "breached": False,
    }
    mock_response.raise_for_status = lambda: None

    with patch("httpx.Client") as mock_httpx:
        mock_post = mock_httpx.return_value.__enter__.return_value.post
        mock_post.return_value = mock_response
        client.record_usage(
            scope_type="agent",
            scope_value="agent-1",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=0,
            completion_tokens=0,
        )

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["X-API-Key"] == "secret-key"
