"""Functional tests: getInflationRate, getInflationGovernor, getInflationReward."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_inflation_rate(rpc_client: RpcClient) -> None:
    """getInflationRate returns rate components."""
    result = await rpc_client.get_inflation_rate()
    assert "total" in result
    assert "validator" in result
    assert "foundation" in result
    assert "epoch" in result
    assert isinstance(result["total"], float)
    assert result["total"] >= 0


async def test_inflation_governor(rpc_client: RpcClient) -> None:
    """getInflationGovernor returns governance parameters."""
    result = await rpc_client.request("getInflationGovernor")
    assert "initial" in result
    assert "terminal" in result
    assert "taper" in result
    assert result["initial"] >= result["terminal"]


async def test_inflation_rate_epoch_matches(rpc_client: RpcClient) -> None:
    """Inflation rate epoch matches current epoch info."""
    inflation = await rpc_client.get_inflation_rate()
    epoch_info = await rpc_client.get_epoch_info()
    assert inflation["epoch"] == epoch_info["epoch"]
