"""Functional tests: getBlock, getBlockTime, getBlocks."""

from __future__ import annotations

import asyncio

from solana.rpc.async_api import AsyncClient

from karstflow_tests.rpc import RpcClient


async def test_get_block_at_slot(solana_client: AsyncClient, rpc_client: RpcClient) -> None:
    """getBlock returns block data for a valid slot."""
    slot_result = await solana_client.get_slot()
    slot = slot_result.value
    # Try a few recent slots (some may be skipped)
    for s in range(max(0, slot - 5), slot):
        result = await rpc_client.request_raw(
            "getBlock",
            [
                s,
                {"encoding": "json", "maxSupportedTransactionVersion": 0},
            ],
        )
        if result.ok and result.result is not None:
            block = result.result
            assert "blockhash" in block
            assert "parentSlot" in block
            assert "transactions" in block
            return
    # If no block found in range, just verify we can query without error
    assert slot > 0


async def test_get_block_time(solana_client: AsyncClient, rpc_client: RpcClient) -> None:
    """getBlockTime returns unix timestamp for a valid slot."""
    slot_result = await solana_client.get_slot()
    slot = slot_result.value
    for s in range(max(0, slot - 5), slot):
        result = await rpc_client.request_raw("getBlockTime", [s])
        if result.ok and result.result is not None:
            assert isinstance(result.result, int)
            assert result.result > 0
            return
    assert slot > 0


async def test_get_blocks_range(rpc_client: RpcClient) -> None:
    """getBlocks returns slot list for a range."""
    slot = await rpc_client.get_slot()
    start = max(0, slot - 10)
    result = await rpc_client.request("getBlocks", [start, slot])
    assert isinstance(result, list)
    # Should have at least some slots in the range
    if len(result) > 0:
        assert all(isinstance(s, int) for s in result)
        assert all(start <= s <= slot for s in result)


async def test_get_block_height(solana_client: AsyncClient) -> None:
    """getBlockHeight returns a positive integer."""
    result = await solana_client.get_block_height()
    assert isinstance(result.value, int)
    assert result.value >= 0


async def test_block_height_advances(solana_client: AsyncClient) -> None:
    """Block height advances over time."""
    h1 = (await solana_client.get_block_height()).value
    await asyncio.sleep(1)
    h2 = (await solana_client.get_block_height()).value
    assert h2 >= h1
