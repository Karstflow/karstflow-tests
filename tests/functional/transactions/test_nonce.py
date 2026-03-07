"""Functional tests: Nonce accounts (durable transactions)."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import create_nonce_account
from tests.helpers.setup import funded_sender


async def test_create_nonce_account(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Creating a nonce account succeeds."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    nonce_kp = await create_nonce_account(solana_client, payer)

    result = await solana_client.get_account_info(nonce_kp.pubkey())
    assert result.value is not None
    assert result.value.lamports > 0


async def test_nonce_account_has_data(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Nonce account contains initialized nonce data (80 bytes)."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    nonce_kp = await create_nonce_account(solana_client, payer)

    result = await solana_client.get_account_info(nonce_kp.pubkey())
    assert result.value is not None
    assert len(result.value.data) == 80


async def test_nonce_account_owned_by_system(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Nonce account is owned by the system program."""
    from karstflow_tests.programs import SYSTEM_PROGRAM

    payer = await funded_sender(solana_client, test_config.rpc_url)
    nonce_kp = await create_nonce_account(solana_client, payer)

    result = await solana_client.get_account_info(nonce_kp.pubkey())
    assert result.value is not None
    assert str(result.value.owner) == str(SYSTEM_PROGRAM)
