"""Smoke tests: getHealth, getVersion."""

from karstflow_tests.rpc import RpcClient


async def test_get_health(rpc_client: RpcClient):
    result = await rpc_client.get_health()
    assert result == "ok"


async def test_get_version(rpc_client: RpcClient):
    result = await rpc_client.get_version()
    assert "solana-core" in result
    assert isinstance(result["solana-core"], str)
