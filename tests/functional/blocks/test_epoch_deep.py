"""Functional tests: epoch schedule and rent exemption edge cases."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_epoch_schedule_slots_per_epoch_positive(rpc_client: RpcClient) -> None:
    """Epoch schedule has positive slotsPerEpoch."""
    schedule = await rpc_client.get_epoch_schedule()
    assert schedule["slotsPerEpoch"] > 0


async def test_epoch_schedule_has_warmup(rpc_client: RpcClient) -> None:
    """Epoch schedule includes warmup field."""
    schedule = await rpc_client.get_epoch_schedule()
    assert "warmup" in schedule
    assert isinstance(schedule["warmup"], bool)


async def test_epoch_schedule_first_normal_epoch(rpc_client: RpcClient) -> None:
    """Epoch schedule has firstNormalEpoch and firstNormalSlot."""
    schedule = await rpc_client.get_epoch_schedule()
    assert "firstNormalEpoch" in schedule
    assert "firstNormalSlot" in schedule
    assert schedule["firstNormalEpoch"] >= 0
    assert schedule["firstNormalSlot"] >= 0


async def test_slot_index_less_than_slots_in_epoch(rpc_client: RpcClient) -> None:
    """Current slot index < slots in epoch."""
    info = await rpc_client.get_epoch_info()
    assert info["slotIndex"] < info["slotsInEpoch"]


async def test_absolute_slot_gte_block_height(rpc_client: RpcClient) -> None:
    """absoluteSlot >= blockHeight (slots may be skipped)."""
    info = await rpc_client.get_epoch_info()
    assert info["absoluteSlot"] >= info["blockHeight"]


async def test_rent_larger_data_more_lamports(rpc_client: RpcClient) -> None:
    """Rent exemption increases with data size."""
    small = await rpc_client.get_minimum_balance_for_rent_exemption(10)
    large = await rpc_client.get_minimum_balance_for_rent_exemption(1000)
    assert large > small


async def test_rent_zero_bytes_has_minimum(rpc_client: RpcClient) -> None:
    """Even 0-byte account requires some rent exemption."""
    rent = await rpc_client.get_minimum_balance_for_rent_exemption(0)
    assert rent > 0


async def test_rent_token_account_size(rpc_client: RpcClient) -> None:
    """Rent for token account size (165 bytes) is reasonable."""
    rent = await rpc_client.get_minimum_balance_for_rent_exemption(165)
    # Should be in the range of ~2M lamports
    assert 1_000_000 < rent < 10_000_000
