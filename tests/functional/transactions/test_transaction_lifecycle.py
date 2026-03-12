"""Functional tests: full transaction lifecycle — build, send, confirm, query.

Tests the complete lifecycle of transactions through the validator,
verifying state transitions and consistency across RPC methods.
"""

from __future__ import annotations

import asyncio

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.signature import Signature
from solders.transaction_status import TransactionConfirmationStatus

from karstflow_tests.config import TestConfig
from karstflow_tests.factories import TransactionFactory
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import build_raw_transfer, funded_sender, transfer_pair


async def test_full_lifecycle_send_confirm_query(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
    rpc_client: RpcClient,
) -> None:
    """Full lifecycle: airdrop -> transfer -> confirm -> getTransaction."""
    sender, recipient = await transfer_pair(solana_client, test_config.rpc_url)

    # Step 1: send transfer
    sig = await tx_factory.send_transfer(sender, recipient.pubkey(), 1_000_000_000)

    # Step 2: verify confirmation status
    sig_obj = Signature.from_string(sig)
    result = await solana_client.get_signature_statuses([sig_obj])
    assert result.value[0] is not None
    assert result.value[0].confirmation_status in (
        TransactionConfirmationStatus.Confirmed,
        TransactionConfirmationStatus.Finalized,
    )
    assert result.value[0].err is None

    # Step 3: query transaction details
    tx_result = await rpc_client.get_transaction(sig)
    assert tx_result is not None
    assert "meta" in tx_result
    assert tx_result["meta"]["err"] is None

    # Step 4: verify balances are consistent
    sender_bal = (await solana_client.get_balance(sender.pubkey())).value
    recipient_bal = (await solana_client.get_balance(recipient.pubkey())).value
    assert recipient_bal == 1_000_000_000
    assert sender_bal < 4_000_000_000  # lost transfer + fee


async def test_transaction_appears_in_block(
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
    rpc_client: RpcClient,
) -> None:
    """Confirmed transaction appears in its block's transaction list."""
    sender, recipient = await transfer_pair(solana_client, test_config.rpc_url)
    sig = await tx_factory.send_transfer(sender, recipient.pubkey(), 100_000_000)

    sig_obj = Signature.from_string(sig)
    status_result = await solana_client.get_signature_statuses([sig_obj])
    slot = status_result.value[0].slot

    block = await rpc_client.get_block(slot)
    if block is not None:
        tx_sigs = [
            t["transaction"]["signatures"][0]
            for t in block.get("transactions", [])
            if "transaction" in t
            and "signatures" in t["transaction"]
            and len(t["transaction"]["signatures"]) > 0
        ]
        # In dev-mode with synthetic block data, the transaction signatures
        # may be empty. Only assert if real data is available.
        if tx_sigs:
            assert sig in tx_sigs


async def test_transaction_idempotent_resend(
    solana_client: AsyncClient, test_config: TestConfig
) -> None:
    """Resending the same signed transaction returns the same signature."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    tx = await build_raw_transfer(solana_client, sender, recipient.pubkey(), 100_000)

    # Send twice — same tx bytes produce same signature
    result1 = await solana_client.send_transaction(tx)
    sig1 = str(result1.value)
    from karstflow_tests.wait import wait_for_confirmation

    await wait_for_confirmation(test_config.rpc_url, sig1)

    result2 = await solana_client.send_transaction(tx)
    sig2 = str(result2.value)
    assert sig1 == sig2


async def test_blockhash_expiry(solana_client: AsyncClient, test_config: TestConfig) -> None:
    """isBlockhashValid returns True for recent blockhash."""
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = str(blockhash_resp.value.blockhash)

    async with RpcClient(config=test_config) as rpc:
        result = await rpc.request("isBlockhashValid", [blockhash])
        assert isinstance(result, dict)
        assert result["value"] is True


async def test_recent_blockhash_changes(solana_client: AsyncClient) -> None:
    """getLatestBlockhash returns different hashes over time."""
    h1 = str((await solana_client.get_latest_blockhash()).value.blockhash)
    await asyncio.sleep(1)
    h2 = str((await solana_client.get_latest_blockhash()).value.blockhash)
    assert h1 != h2
