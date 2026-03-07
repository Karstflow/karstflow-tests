"""Smoke tests: getGenesisHash, getSlot, epoch info."""

from solana.rpc.async_api import AsyncClient

from karstflow_tests.client import ValidatorClient


async def test_get_genesis_hash(solana_client: AsyncClient) -> None:
    result = await solana_client.get_genesis_hash()
    genesis_hash = str(result.value)
    assert len(genesis_hash) > 30  # base58-encoded 32-byte hash


async def test_get_slot_advances(solana_client: AsyncClient) -> None:
    result = await solana_client.get_slot()
    assert isinstance(result.value, int)
    assert result.value > 0


async def test_epoch_info_via_test_client(test_client: ValidatorClient) -> None:
    """Verify ValidatorClient.get_epoch_info() returns parsed model."""
    info = await test_client.get_epoch_info()
    assert info.epoch >= 0
    assert info.slots_in_epoch > 0
    assert info.absolute_slot >= 0


async def test_batch_health_and_slot(rpc_client) -> None:
    """Verify batch RPC works with multiple methods."""
    responses = await rpc_client.batch(
        [
            ("getHealth", None),
            ("getSlot", None),
            ("getBlockHeight", None),
        ]
    )
    assert len(responses) == 3
    # Health may transiently report unhealthy during startup.
    assert responses[1].ok
    assert responses[2].ok
    assert isinstance(responses[1].result, int)
