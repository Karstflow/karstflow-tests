"""Smoke tests: getHealth, getVersion."""

from solana.rpc.async_api import AsyncClient

from karstflow_tests.client import ValidatorClient


async def test_get_health(solana_client: AsyncClient) -> None:
    result = await solana_client.get_health()
    assert result.value == "ok"


async def test_get_version(solana_client: AsyncClient) -> None:
    result = await solana_client.get_version()
    assert result.value is not None
    assert "solana-core" in result.value


async def test_health_via_test_client(test_client: ValidatorClient) -> None:
    """Verify ValidatorClient.is_healthy() works."""
    healthy = await test_client.is_healthy()
    assert healthy is True


async def test_version_via_raw_rpc(rpc_client) -> None:
    """Verify raw RPC client returns version."""
    from karstflow_tests.rpc import RpcClient

    assert isinstance(rpc_client, RpcClient)
    version = await rpc_client.get_version()
    assert "solana-core" in version
