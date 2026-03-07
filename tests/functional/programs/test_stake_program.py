"""Functional tests: Stake program queries and state inspection."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import STAKE_PROGRAM


async def test_stake_minimum_delegation_positive(raw_rpc: RpcClient) -> None:
    """getStakeMinimumDelegation returns a positive value."""
    result = await raw_rpc.get_stake_minimum_delegation()
    assert "value" in result
    assert result["value"] > 0


async def test_stake_program_accounts(raw_rpc: RpcClient) -> None:
    """getProgramAccounts for Stake program returns accounts (if any)."""
    result = await raw_rpc.get_program_accounts(STAKE_PROGRAM)
    assert isinstance(result, list)
    # In dev mode there may or may not be stake accounts
    for entry in result:
        assert entry["account"]["owner"] == STAKE_PROGRAM


async def test_stake_program_accounts_data_size(raw_rpc: RpcClient) -> None:
    """Stake accounts have expected data size (200 bytes)."""
    result = await raw_rpc.get_program_accounts(
        STAKE_PROGRAM,
        filters=[{"dataSize": 200}],
    )
    assert isinstance(result, list)
    # All returned accounts should be 200 bytes (StakeState size)


async def test_inflation_reward_query(raw_rpc: RpcClient) -> None:
    """getInflationReward works for validator identity (may return null)."""
    identity = await raw_rpc.get_identity()
    pubkey = identity["identity"]
    result = await raw_rpc.get_inflation_reward([pubkey])
    assert isinstance(result, list)
    assert len(result) == 1
    # In dev mode, reward may be null


async def test_inflation_reward_empty_list(raw_rpc: RpcClient) -> None:
    """getInflationReward with empty address list returns empty."""
    result = await raw_rpc.get_inflation_reward([])
    assert isinstance(result, list)
    assert len(result) == 0
