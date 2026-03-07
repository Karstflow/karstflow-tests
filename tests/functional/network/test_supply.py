"""Functional tests: getSupply, getStakeMinimumDelegation."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_get_supply(rpc_client: RpcClient) -> None:
    """getSupply returns total, circulating, and non-circulating amounts."""
    result = await rpc_client.get_supply()
    assert "value" in result
    supply = result["value"]
    assert "total" in supply
    assert "circulating" in supply
    assert "nonCirculating" in supply
    assert supply["total"] > 0
    assert supply["circulating"] >= 0
    assert supply["total"] >= supply["circulating"]


async def test_supply_total_equals_sum(rpc_client: RpcClient) -> None:
    """Total supply = circulating + non-circulating."""
    result = await rpc_client.get_supply()
    supply = result["value"]
    assert supply["total"] == supply["circulating"] + supply["nonCirculating"]


async def test_get_stake_minimum_delegation(rpc_client: RpcClient) -> None:
    """getStakeMinimumDelegation returns a positive integer."""
    result = await rpc_client.request("getStakeMinimumDelegation")
    assert isinstance(result, dict)
    assert "value" in result
    assert result["value"] > 0
