"""Functional tests: requestAirdrop RPC method."""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from tests.helpers.setup import airdrop_and_confirm


async def test_airdrop_returns_signature(
    solana_client: AsyncClient, test_config: TestConfig
) -> None:
    """Airdrop returns a valid transaction signature."""
    kp = Keypair()
    sig = await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), 1_000_000_000)
    assert len(sig) > 40


async def test_airdrop_confirms(solana_client: AsyncClient, test_config: TestConfig) -> None:
    """Airdrop transaction reaches confirmed status and balance matches."""
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), 500_000_000)
    result = await solana_client.get_balance(kp.pubkey())
    assert result.value == 500_000_000


async def test_multiple_airdrops_accumulate(
    solana_client: AsyncClient, test_config: TestConfig
) -> None:
    """Multiple airdrops to same account accumulate balance."""
    kp = Keypair()
    for _ in range(3):
        await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), 1_000_000_000)

    result = await solana_client.get_balance(kp.pubkey())
    assert result.value == 3_000_000_000


@pytest.mark.parametrize(
    "amount",
    [1, 1_000, 1_000_000, 1_000_000_000],
    ids=["1_lamport", "1K_lamports", "1M_lamports", "1_SOL"],
)
async def test_airdrop_various_amounts(
    solana_client: AsyncClient, test_config: TestConfig, amount: int
) -> None:
    """Airdrop works for various amounts."""
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), amount)
    result = await solana_client.get_balance(kp.pubkey())
    assert result.value == amount
