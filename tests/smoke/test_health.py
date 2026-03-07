"""Smoke tests: getHealth, getVersion."""

from solana.rpc.async_api import AsyncClient


async def test_get_health(solana_client: AsyncClient) -> None:
    result = await solana_client.get_health()
    assert result.value == "ok"


async def test_get_version(solana_client: AsyncClient) -> None:
    result = await solana_client.get_version()
    assert result.value is not None
    assert "solana-core" in result.value
