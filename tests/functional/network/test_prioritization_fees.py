"""Functional tests: getRecentPrioritizationFees, slot leader, max slots."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_recent_prioritization_fees(raw_rpc: RpcClient) -> None:
    """getRecentPrioritizationFees returns a list."""
    result = await raw_rpc.get_recent_prioritization_fees()
    assert isinstance(result, list)
    for entry in result[:5]:
        assert "slot" in entry
        assert "prioritizationFee" in entry
        assert isinstance(entry["prioritizationFee"], int)


async def test_slot_leader_is_pubkey(raw_rpc: RpcClient) -> None:
    """getSlotLeader returns a base58-encoded pubkey."""
    leader = await raw_rpc.get_slot_leader()
    assert isinstance(leader, str)
    assert len(leader) >= 32


async def test_slot_leaders_range(raw_rpc: RpcClient) -> None:
    """getSlotLeaders returns pubkeys for requested range."""
    slot = await raw_rpc.get_slot()
    leaders = await raw_rpc.get_slot_leaders(slot, 10)
    assert isinstance(leaders, list)
    assert len(leaders) == 10
    for leader in leaders:
        assert isinstance(leader, str)
        assert len(leader) >= 32


async def test_max_retransmit_slot(raw_rpc: RpcClient) -> None:
    """getMaxRetransmitSlot returns a non-negative integer."""
    slot = await raw_rpc.get_max_retransmit_slot()
    assert isinstance(slot, int)
    assert slot >= 0


async def test_max_shred_insert_slot(raw_rpc: RpcClient) -> None:
    """getMaxShredInsertSlot returns a non-negative integer."""
    slot = await raw_rpc.get_max_shred_insert_slot()
    assert isinstance(slot, int)
    assert slot >= 0


async def test_minimum_ledger_slot(raw_rpc: RpcClient) -> None:
    """minimumLedgerSlot returns a non-negative integer."""
    slot = await raw_rpc.minimum_ledger_slot()
    assert isinstance(slot, int)
    assert slot >= 0


async def test_stake_minimum_delegation(raw_rpc: RpcClient) -> None:
    """getStakeMinimumDelegation returns delegation info."""
    result = await raw_rpc.get_stake_minimum_delegation()
    assert isinstance(result, dict)
    assert "value" in result
    assert isinstance(result["value"], int)
    assert result["value"] > 0


async def test_inflation_governor(raw_rpc: RpcClient) -> None:
    """getInflationGovernor returns rate parameters."""
    result = await raw_rpc.get_inflation_governor()
    assert isinstance(result, dict)
    assert "initial" in result
    assert "terminal" in result
    assert "taper" in result
    assert result["initial"] >= result["terminal"]
