"""Functional tests: supply and inflation deep coverage."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_supply_total_gte_circulating(rpc_client: RpcClient) -> None:
    """Total supply >= circulating supply."""
    result = await rpc_client.get_supply()
    value = result["value"]
    assert value["total"] >= value["circulating"]


async def test_supply_non_circulating_accounts(rpc_client: RpcClient) -> None:
    """Supply response includes nonCirculatingAccounts list."""
    result = await rpc_client.get_supply()
    value = result["value"]
    assert "nonCirculatingAccounts" in value
    assert isinstance(value["nonCirculatingAccounts"], list)


async def test_supply_circulating_positive(rpc_client: RpcClient) -> None:
    """Circulating supply is positive."""
    result = await rpc_client.get_supply()
    assert result["value"]["circulating"] > 0


async def test_inflation_governor_fields(rpc_client: RpcClient) -> None:
    """Inflation governor has all required fields."""
    gov = await rpc_client.get_inflation_governor()
    required = ["initial", "terminal", "taper", "foundation", "foundationTerm"]
    for field in required:
        assert field in gov, f"Missing inflation governor field: {field}"


async def test_inflation_governor_rates_in_range(rpc_client: RpcClient) -> None:
    """Inflation governor rates are in valid range [0, 1]."""
    gov = await rpc_client.get_inflation_governor()
    for field in ["initial", "terminal", "taper", "foundation"]:
        val = gov[field]
        assert 0.0 <= val <= 1.0, f"{field}={val} out of range"


async def test_inflation_rate_has_fields(rpc_client: RpcClient) -> None:
    """Inflation rate has total, validator, foundation fields."""
    rate = await rpc_client.get_inflation_rate()
    assert "total" in rate
    assert "validator" in rate
    assert "foundation" in rate
    assert "epoch" in rate
    assert rate["epoch"] >= 0
