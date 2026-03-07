"""Smoke tests: getGenesisHash, getSlot."""

from solana.rpc.async_api import AsyncClient


async def test_get_genesis_hash(solana_client: AsyncClient) -> None:
    result = await solana_client.get_genesis_hash()
    genesis_hash = str(result.value)
    assert len(genesis_hash) > 30  # base58-encoded 32-byte hash


async def test_get_slot_advances(solana_client: AsyncClient) -> None:
    result = await solana_client.get_slot()
    assert isinstance(result.value, int)
    assert result.value > 0
