"""Functional tests: sendTransaction RPC method."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.factories import TransactionFactory
from karstflow_tests.wait import wait_for_confirmation
from tests.helpers.setup import funded_sender


async def test_send_signed_transaction(
    solana_client: AsyncClient, test_config: TestConfig, tx_factory: TransactionFactory
) -> None:
    """Properly signed transaction is accepted."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    tx = await tx_factory.build_transfer(sender, sender.pubkey(), 100_000_000)
    result = await solana_client.send_transaction(tx)
    sig = str(result.value)
    assert len(sig) > 40
    await wait_for_confirmation(test_config.rpc_url, sig)


async def test_send_transaction_returns_signature(
    solana_client: AsyncClient, test_config: TestConfig, tx_factory: TransactionFactory
) -> None:
    """sendTransaction returns a base58 signature, and the transaction confirms on-chain."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 2_000_000_000)
    tx = await tx_factory.build_transfer(sender, sender.pubkey(), 1_000)
    result = await solana_client.send_transaction(tx)
    sig = str(result.value)
    # Solana signatures are 88 chars in base58
    assert 80 <= len(sig) <= 90
    # Wait for on-chain confirmation
    await wait_for_confirmation(test_config.rpc_url, sig)
    # Verify the transaction is visible via getSignatureStatuses
    statuses = await solana_client.get_signature_statuses([result.value])
    assert statuses.value[0] is not None
