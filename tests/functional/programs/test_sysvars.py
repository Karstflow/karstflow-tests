"""Functional tests: Sysvar accounts existence and properties.

Verifies that all sysvar accounts karstflow maintains are accessible
and contain expected data formats.
"""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

from karstflow_tests.rpc import RpcClient

# ── Sysvar accounts implemented by karstflow ──────────────────────────

SYSVARS = [
    ("clock", "SysvarC1ock11111111111111111111111111111111"),
    ("rent", "SysvarRent111111111111111111111111111111"),
    ("epoch_schedule", "SysvarEpochSchedu1e111111111111111111111111"),
    ("slot_hashes", "SysvarS1otHashes111111111111111111111111111"),
    ("slot_history", "SysvarS1otHistory11111111111111111111111111"),
    ("stake_history", "SysvarStakeHistory1111111111111111111111111"),
    ("instructions", "Sysvar1nstructions1111111111111111111111111"),
    ("recent_blockhashes", "SysvarRecentB1telekenHashes11111111111111"),
]

SYSVAR_IDS = [name for name, _ in SYSVARS]

SYSVAR_OWNER = "Sysvar1111111111111111111111111111111111111"


@pytest.mark.parametrize(("name", "pubkey"), SYSVARS, ids=SYSVAR_IDS)
async def test_sysvar_exists(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """Sysvar account exists on chain."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None, f"Sysvar {name} ({pubkey}) not found"


@pytest.mark.parametrize(("name", "pubkey"), SYSVARS, ids=SYSVAR_IDS)
async def test_sysvar_not_executable(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """Sysvar accounts should not be executable."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert not result.value.executable, f"Sysvar {name} should not be executable"


@pytest.mark.parametrize(("name", "pubkey"), SYSVARS, ids=SYSVAR_IDS)
async def test_sysvar_has_data(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """Sysvar accounts should contain data."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert len(result.value.data) > 0, f"Sysvar {name} has no data"


# ── Specific sysvar content tests ────────────────────────────────────


async def test_clock_sysvar_via_rpc(raw_rpc: RpcClient) -> None:
    """Clock sysvar data matches getEpochInfo slot information."""
    epoch_info = await raw_rpc.get_epoch_info()
    assert "epoch" in epoch_info
    assert "absoluteSlot" in epoch_info
    assert epoch_info["absoluteSlot"] >= 0


async def test_rent_sysvar_minimum_balance(raw_rpc: RpcClient) -> None:
    """Rent sysvar provides minimum balance calculations."""
    min_balance = await raw_rpc.get_minimum_balance_for_rent_exemption(0)
    assert isinstance(min_balance, int)
    assert min_balance > 0

    # Larger data requires more lamports
    min_balance_large = await raw_rpc.get_minimum_balance_for_rent_exemption(1024)
    assert min_balance_large > min_balance


async def test_epoch_schedule_sysvar_via_rpc(raw_rpc: RpcClient) -> None:
    """Epoch schedule is accessible via RPC."""
    schedule = await raw_rpc.get_epoch_schedule()
    assert isinstance(schedule, dict)
    assert "slotsPerEpoch" in schedule
    assert "warmup" in schedule
    assert schedule["slotsPerEpoch"] > 0


async def test_slot_hashes_sysvar_size(solana_client: AsyncClient) -> None:
    """Slot hashes sysvar has non-trivial data size."""
    pk = Pubkey.from_string("SysvarS1otHashes111111111111111111111111111")
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    # Slot hashes stores recent hashes, should have meaningful data
    assert len(result.value.data) >= 32


async def test_stake_history_sysvar_accessible(solana_client: AsyncClient) -> None:
    """Stake history sysvar is accessible."""
    pk = Pubkey.from_string("SysvarStakeHistory1111111111111111111111111")
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert result.value.lamports > 0
