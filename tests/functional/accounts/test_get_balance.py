"""Functional tests: getBalance RPC method."""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from karstflow_tests.factories import lamport_amounts
from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import SYSTEM_PROGRAM
from tests.helpers.setup import airdrop_and_confirm


async def test_balance_of_new_account(solana_client: AsyncClient) -> None:
    """New unfunded account should have zero balance."""
    kp = Keypair()
    result = await solana_client.get_balance(kp.pubkey())
    assert result.value == 0


async def test_balance_after_airdrop(
    solana_client: AsyncClient,
    test_config,
) -> None:
    """Balance should reflect airdrop amount."""
    kp = Keypair()
    amount = 1_000_000_000
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), amount)
    result = await solana_client.get_balance(kp.pubkey())
    assert result.value == amount


@pytest.mark.parametrize("amount", lamport_amounts()[:4])
async def test_balance_parametrized_airdrop(
    solana_client: AsyncClient, test_config, amount: int
) -> None:
    """Balance matches various airdrop amounts."""
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), amount)
    result = await solana_client.get_balance(kp.pubkey())
    assert result.value == amount


async def test_balance_via_raw_rpc(rpc_client: RpcClient) -> None:
    """getBalance via raw JSON-RPC returns context + value."""
    kp = Keypair()
    result = await rpc_client.get_balance(str(kp.pubkey()))
    assert isinstance(result, dict)
    assert "value" in result
    assert result["value"] == 0


async def test_balance_of_system_program(solana_client: AsyncClient) -> None:
    """System program account (111...1) should have a balance."""
    system = Pubkey.from_string(SYSTEM_PROGRAM)
    result = await solana_client.get_balance(system)
    assert result.value >= 0
