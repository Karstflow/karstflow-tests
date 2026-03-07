"""Functional tests: getBlockProduction, getBlockCommitment, getFirstAvailableBlock."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_block_production_returns_data(raw_rpc: RpcClient) -> None:
    """getBlockProduction returns leader slots and blocks produced."""
    result = await raw_rpc.get_block_production()
    assert isinstance(result, dict)
    assert "value" in result
    value = result["value"]
    assert "byIdentity" in value
    assert "range" in value
    assert "firstSlot" in value["range"]


async def test_block_production_has_validator_entries(raw_rpc: RpcClient) -> None:
    """At least one validator should have produced blocks."""
    result = await raw_rpc.get_block_production()
    by_identity = result["value"]["byIdentity"]
    assert len(by_identity) >= 1
    for _pubkey, (leader_slots, blocks_produced) in by_identity.items():
        assert leader_slots >= 0
        assert blocks_produced >= 0
        assert blocks_produced <= leader_slots


async def test_block_commitment(raw_rpc: RpcClient) -> None:
    """getBlockCommitment returns commitment data for a slot."""
    slot = await raw_rpc.get_slot()
    result = await raw_rpc.get_block_commitment(slot)
    assert isinstance(result, dict)
    assert "totalStake" in result
    assert result["totalStake"] > 0


async def test_first_available_block(raw_rpc: RpcClient) -> None:
    """getFirstAvailableBlock returns a non-negative slot."""
    first = await raw_rpc.get_first_available_block()
    assert isinstance(first, int)
    assert first >= 0


async def test_first_available_block_before_current(raw_rpc: RpcClient) -> None:
    """First available block is at or before current slot."""
    first = await raw_rpc.get_first_available_block()
    current = await raw_rpc.get_slot()
    assert first <= current


async def test_blocks_with_limit(raw_rpc: RpcClient) -> None:
    """getBlocksWithLimit returns confirmed blocks starting from a slot."""
    slot = await raw_rpc.get_slot()
    start = max(0, slot - 10)
    blocks = await raw_rpc.get_blocks_with_limit(start, 5)
    assert isinstance(blocks, list)
    assert len(blocks) <= 5
    for b in blocks:
        assert isinstance(b, int)
        assert b >= start


async def test_highest_snapshot_slot(raw_rpc: RpcClient) -> None:
    """getHighestSnapshotSlot returns snapshot information."""
    resp = await raw_rpc.request_raw("getHighestSnapshotSlot")
    # May return error if no snapshots exist in dev mode, that's acceptable
    if resp.ok:
        result = resp.result
        assert isinstance(result, dict)
        assert "full" in result
    else:
        assert resp.error is not None
