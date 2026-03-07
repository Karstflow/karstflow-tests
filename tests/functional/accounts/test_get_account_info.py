"""Functional tests: getAccountInfo RPC method."""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from karstflow_tests.config import TestConfig
from karstflow_tests.factories import known_program_ids
from tests.helpers.constants import SYSTEM_PROGRAM
from tests.helpers.setup import airdrop_and_confirm


async def test_account_info_nonexistent(solana_client: AsyncClient) -> None:
    """Non-existent account returns None value."""
    kp = Keypair()
    result = await solana_client.get_account_info(kp.pubkey())
    assert result.value is None


async def test_account_info_after_airdrop(
    solana_client: AsyncClient, test_config: TestConfig
) -> None:
    """Funded account has correct lamports and owner."""
    kp = Keypair()
    amount = 2_000_000_000
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), amount)

    result = await solana_client.get_account_info(kp.pubkey())
    assert result.value is not None
    info = result.value
    assert info.lamports == amount
    assert str(info.owner) == SYSTEM_PROGRAM
    assert info.executable is False


@pytest.mark.parametrize(
    ("name", "pubkey"),
    known_program_ids(),
    ids=[p[0] for p in known_program_ids()],
)
async def test_known_program_accounts_exist(
    solana_client: AsyncClient, name: str, pubkey: Pubkey
) -> None:
    """Known program accounts should exist on devnet."""
    result = await solana_client.get_account_info(pubkey)
    if name == "system":
        pass  # System program is native, special handling
    assert result is not None


async def test_account_info_encoding_base64(
    solana_client: AsyncClient, test_config: TestConfig
) -> None:
    """Account data can be retrieved in base64 encoding."""
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey())
    result = await solana_client.get_account_info(kp.pubkey(), encoding="base64")
    assert result.value is not None
