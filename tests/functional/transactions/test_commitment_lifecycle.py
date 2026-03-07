"""Functional tests: transaction commitment lifecycle.

Tests that transactions progress through commitment levels correctly:
processed -> confirmed -> finalized.
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.signature import Signature

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender, send_simple_transfer


async def test_transaction_reaches_confirmed(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transaction reaches confirmed status."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
    )

    result = await solana_client.get_signature_statuses([Signature.from_string(sig)])
    status = result.value[0]
    assert status is not None
    assert status.confirmation_status in ("confirmed", "finalized")


async def test_confirmed_transaction_has_slot(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Confirmed transaction has a valid slot."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
    )

    result = await solana_client.get_signature_statuses([Signature.from_string(sig)])
    status = result.value[0]
    assert status is not None
    assert status.slot > 0


async def test_confirmed_transaction_no_error(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Successfully confirmed transaction has no error."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
    )

    result = await solana_client.get_signature_statuses([Signature.from_string(sig)])
    status = result.value[0]
    assert status is not None
    assert status.err is None


async def test_multiple_signatures_status(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Can query status of multiple signatures at once."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    sigs = []
    for _ in range(3):
        recipient = Keypair()
        sig = await send_simple_transfer(
            solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
        )
        sigs.append(sig)

    sig_objs = [Signature.from_string(s) for s in sigs]
    result = await solana_client.get_signature_statuses(sig_objs)
    statuses = result.value
    assert len(statuses) == 3
    for status in statuses:
        assert status is not None
        assert status.err is None


async def test_transaction_visible_in_get_transaction(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Confirmed transaction is retrievable via getTransaction."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 500_000
    )

    tx = await rpc_client.get_transaction(sig)
    assert tx is not None
    assert tx["meta"]["err"] is None
    assert tx["meta"]["fee"] == 5000


async def test_transaction_signatures_for_address(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """getSignaturesForAddress returns the sent transaction."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 500_000
    )

    sigs = await rpc_client.get_signatures_for_address(str(sender.pubkey()), limit=5)
    assert len(sigs) >= 1
    found = any(s["signature"] == sig for s in sigs)
    assert found, f"Signature {sig} not found in recent signatures"
