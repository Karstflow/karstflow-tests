"""Functional tests: SOL transfer transactions."""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.factories import TransactionFactory
from tests.helpers.constants import TRANSFER_AMOUNTS, TRANSFER_AMOUNTS_IDS
from tests.helpers.setup import funded_sender, transfer_pair


async def test_basic_transfer(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
) -> None:
    """Basic SOL transfer succeeds and updates balances."""
    sender, recipient = await transfer_pair(solana_client, test_config.rpc_url)
    sig = await tx_factory.send_transfer(sender, recipient.pubkey(), 1_000_000_000)
    assert len(sig) > 40

    sender_balance = await solana_client.get_balance(sender.pubkey())
    recipient_balance = await solana_client.get_balance(recipient.pubkey())
    assert recipient_balance.value == 1_000_000_000
    assert sender_balance.value < 4_000_000_000


async def test_transfer_deducts_fee(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
) -> None:
    """Transfer costs more than the amount sent (includes fee)."""
    sender, recipient = await transfer_pair(solana_client, test_config.rpc_url)
    transfer_amount = 1_000_000_000
    await tx_factory.send_transfer(sender, recipient.pubkey(), transfer_amount)

    balance = await solana_client.get_balance(sender.pubkey())
    assert balance.value < 5_000_000_000 - transfer_amount


async def test_transfer_to_self(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
) -> None:
    """Transfer to self should succeed (only fee deducted)."""
    kp = await funded_sender(solana_client, test_config.rpc_url)
    await tx_factory.send_transfer(kp, kp.pubkey(), 1_000_000_000)

    balance = await solana_client.get_balance(kp.pubkey())
    assert balance.value > 4_900_000_000


@pytest.mark.parametrize("amount", TRANSFER_AMOUNTS[:4], ids=TRANSFER_AMOUNTS_IDS[:4])
async def test_transfer_various_amounts(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
    amount: int,
) -> None:
    """Transfers of various amounts succeed."""
    sender, recipient = await transfer_pair(solana_client, test_config.rpc_url)
    await tx_factory.send_transfer(sender, recipient.pubkey(), amount)
    result = await solana_client.get_balance(recipient.pubkey())
    assert result.value == amount


async def test_transfer_multiple_recipients(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
) -> None:
    """Transaction with multiple transfer instructions."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    recipients = [Keypair() for _ in range(3)]
    tx = await tx_factory.build_transfer_many(
        sender, [(r.pubkey(), 500_000_000) for r in recipients]
    )
    resp = await solana_client.send_transaction(tx)
    from karstflow_tests.wait import wait_for_confirmation

    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    for r in recipients:
        bal = await solana_client.get_balance(r.pubkey())
        assert bal.value == 500_000_000
