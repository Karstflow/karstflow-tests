"""Functional tests: simulateTransaction RPC method."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.factories import TransactionFactory
from tests.helpers.setup import funded_sender, transfer_pair


async def test_simulate_valid_transfer(
    solana_client: AsyncClient, test_config: TestConfig, tx_factory: TransactionFactory
) -> None:
    """Simulating a valid transfer returns no error."""
    sender, recipient = await transfer_pair(solana_client, test_config.rpc_url)
    tx = await tx_factory.build_transfer(sender, recipient.pubkey(), 1_000_000_000)
    result = await solana_client.simulate_transaction(tx)
    assert result.value.err is None


async def test_simulate_insufficient_funds(
    solana_client: AsyncClient, test_config: TestConfig, tx_factory: TransactionFactory
) -> None:
    """Simulating transfer with insufficient funds returns error."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 1_000_000)
    tx = await tx_factory.build_transfer(sender, sender.pubkey(), 999_000_000_000)
    result = await solana_client.simulate_transaction(tx)
    assert result.value.err is not None


async def test_simulate_does_not_modify_state(
    solana_client: AsyncClient, test_config: TestConfig, tx_factory: TransactionFactory
) -> None:
    """Simulation should not change actual account balances."""
    amount = 3_000_000_000
    sender, recipient = await transfer_pair(
        solana_client, test_config.rpc_url, sender_lamports=amount
    )
    tx = await tx_factory.build_transfer(sender, recipient.pubkey(), 1_000_000_000)
    await solana_client.simulate_transaction(tx)

    # Balance should remain unchanged after simulation
    sender_balance = await solana_client.get_balance(sender.pubkey())
    recipient_balance = await solana_client.get_balance(recipient.pubkey())
    assert sender_balance.value == amount
    assert recipient_balance.value == 0
