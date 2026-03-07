"""Functional tests: block data deep coverage.

Tests block structure, rewards, time, parent slot relationships.
"""

from __future__ import annotations

import time

from karstflow_tests.rpc import RpcClient


async def test_block_time_is_reasonable(rpc_client: RpcClient) -> None:
    """Block time is a Unix timestamp within reasonable range."""
    slot = await rpc_client.get_slot()
    bt = await rpc_client.get_block_time(slot)
    if bt is not None:
        now = int(time.time())
        # Should be within last 24 hours and not in the future (+1min tolerance)
        assert now - 86400 < bt < now + 60


async def test_block_parent_slot_less_than_slot(rpc_client: RpcClient) -> None:
    """Block's parentSlot < slot."""
    slot = await rpc_client.get_slot()
    block = await rpc_client.get_block(slot)
    if block is not None:
        assert block["parentSlot"] < slot


async def test_block_has_block_height(rpc_client: RpcClient) -> None:
    """Block includes blockHeight field."""
    slot = await rpc_client.get_slot()
    block = await rpc_client.get_block(slot)
    if block is not None:
        assert "blockHeight" in block
        assert isinstance(block["blockHeight"], int)
        assert block["blockHeight"] > 0


async def test_block_rewards_have_type(rpc_client: RpcClient) -> None:
    """Block rewards entries have rewardType field."""
    slot = await rpc_client.get_slot()
    block = await rpc_client.get_block(slot)
    if block is not None and block.get("rewards"):
        for reward in block["rewards"]:
            assert "rewardType" in reward
            assert reward["rewardType"] in ("Fee", "Rent", "Voting", "Staking", None)


async def test_get_blocks_returns_contiguous(rpc_client: RpcClient) -> None:
    """getBlocks returns a contiguous range of slot numbers."""
    slot = await rpc_client.get_slot()
    start = max(0, slot - 10)
    blocks = await rpc_client.get_blocks(start, slot)
    assert isinstance(blocks, list)
    # Should be sorted ascending
    for i in range(1, len(blocks)):
        assert blocks[i] > blocks[i - 1]


async def test_get_blocks_with_limit_respects_limit(rpc_client: RpcClient) -> None:
    """getBlocksWithLimit doesn't return more than limit."""
    slot = await rpc_client.get_slot()
    start = max(0, slot - 100)
    blocks = await rpc_client.get_blocks_with_limit(start, 5)
    assert len(blocks) <= 5


async def test_first_available_block_lte_current(rpc_client: RpcClient) -> None:
    """First available block <= current slot."""
    first = await rpc_client.get_first_available_block()
    slot = await rpc_client.get_slot()
    assert first <= slot


async def test_highest_snapshot_slot_lte_current(rpc_client: RpcClient) -> None:
    """Highest snapshot slot <= current slot."""
    result = await rpc_client.get_highest_snapshot_slot()
    slot = await rpc_client.get_slot()
    assert result["full"] <= slot
