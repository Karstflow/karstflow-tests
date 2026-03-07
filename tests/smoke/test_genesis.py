"""Smoke tests: getGenesisHash, getSlot."""

from karstflow_tests.rpc import RpcClient


async def test_get_genesis_hash(rpc_client: RpcClient):
    result = await rpc_client.get_genesis_hash()
    assert isinstance(result, str)
    assert len(result) > 30  # base58-encoded 32-byte hash


async def test_get_slot_advances(rpc_client: RpcClient):
    slot = await rpc_client.get_slot()
    assert isinstance(slot, int)
    assert slot > 0
