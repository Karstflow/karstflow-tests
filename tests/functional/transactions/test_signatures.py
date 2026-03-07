"""Functional tests: getSignatureStatuses, getSignaturesForAddress."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.signature import Signature

from karstflow_tests.config import TestConfig
from karstflow_tests.factories import TransactionFactory
from karstflow_tests.wait import wait_for_confirmation


async def test_signature_status_confirmed(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
) -> None:
    """Confirmed transaction has confirmed/finalized status."""
    sender = Keypair()
    resp = await solana_client.request_airdrop(sender.pubkey(), 5_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    recipient = Keypair()
    sig = await tx_factory.send_transfer(sender, recipient.pubkey(), 1_000_000_000)

    sig_obj = Signature.from_string(sig)
    result = await solana_client.get_signature_statuses([sig_obj])
    statuses = result.value
    assert len(statuses) == 1
    assert statuses[0] is not None
    assert statuses[0].confirmation_status in ("confirmed", "finalized")


async def test_signature_status_unknown(solana_client: AsyncClient) -> None:
    """Unknown signature returns None status."""
    fake_sig = Signature.default()
    result = await solana_client.get_signature_statuses([fake_sig])
    statuses = result.value
    assert len(statuses) == 1
    assert statuses[0] is None


async def test_signatures_for_address(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
) -> None:
    """getSignaturesForAddress returns transaction history."""
    sender = Keypair()
    resp = await solana_client.request_airdrop(sender.pubkey(), 10_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    # Send a few transactions
    recipient = Keypair()
    for _ in range(3):
        await tx_factory.send_transfer(sender, recipient.pubkey(), 100_000_000)

    result = await solana_client.get_signatures_for_address(sender.pubkey())
    signatures = result.value
    # At least 3 transfers + 1 airdrop = 4 signatures
    assert len(signatures) >= 3


async def test_signatures_for_address_limit(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
) -> None:
    """getSignaturesForAddress respects limit parameter."""
    sender = Keypair()
    resp = await solana_client.request_airdrop(sender.pubkey(), 10_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    recipient = Keypair()
    for _ in range(5):
        await tx_factory.send_transfer(sender, recipient.pubkey(), 100_000_000)

    result = await solana_client.get_signatures_for_address(sender.pubkey(), limit=2)
    assert len(result.value) <= 2
