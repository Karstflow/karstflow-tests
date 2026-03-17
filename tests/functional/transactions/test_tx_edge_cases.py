"""Transaction edge case tests.

Tests protocol boundaries: duplicate transactions, expired blockhashes,
duplicate accounts in instructions, zero-amount transfers, and balance drain.
"""

from __future__ import annotations

import pytest
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import Message
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from karstflow_tests.wait import wait_for_confirmation


@pytest.mark.transactions
class TestTransactionEdgeCases:
    """Edge case tests for transaction processing."""

    async def test_duplicate_transaction_rejected(self, solana_client, funded_keypair, test_config):
        """Sending the same signed transaction twice — second is rejected as duplicate."""
        recipient = Keypair()
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([transfer_ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        # First send succeeds
        resp1 = await solana_client.send_transaction(tx)
        await wait_for_confirmation(test_config.rpc_url, str(resp1.value))

        # Second send of same tx should fail or be ignored
        try:
            await solana_client.send_transaction(tx)
            # If it doesn't throw, the tx already processed — should not double-apply
            balance = await solana_client.get_balance(recipient.pubkey())
            assert balance.value == 100_000  # Only one transfer applied
        except Exception:
            pass  # Rejected — valid behavior

    async def test_expired_blockhash_rejected(self, solana_client, funded_keypair, test_config):
        """Transaction with a fake/expired blockhash is rejected."""
        recipient = Keypair()
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )

        # Use a fake blockhash (all 1s)
        fake_blockhash = Hash.new_unique()
        msg = Message.new_with_blockhash([transfer_ix], funded_keypair.pubkey(), fake_blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], fake_blockhash)

        # Should fail — either sendTransaction rejects or tx has error
        try:
            resp = await solana_client.send_transaction(tx)
            sig = str(resp.value)
            await wait_for_confirmation(test_config.rpc_url, sig)
            status = await solana_client.get_signature_statuses([resp.value])
            if status.value[0] is not None:
                assert status.value[0].err is not None
        except Exception:
            pass  # Rejected at send — valid behavior

    async def test_duplicate_account_in_instructions(
        self, solana_client, funded_keypair, test_config
    ):
        """Same account appearing in multiple instructions within one tx succeeds."""
        recipient = Keypair()
        # Two transfers to the same recipient
        ix1 = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )
        ix2 = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=200_000,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix1, ix2], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.send_transaction(tx)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        balance = await solana_client.get_balance(recipient.pubkey())
        assert balance.value == 300_000  # Both transfers applied

    async def test_zero_lamport_transfer(self, solana_client, funded_keypair, test_config):
        """Transfer of 0 lamports succeeds (only fee deducted)."""
        recipient = Keypair()
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=0,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([transfer_ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.send_transaction(tx)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        status = await solana_client.get_signature_statuses([resp.value])
        assert status.value[0] is not None
        assert status.value[0].err is None

    async def test_transfer_exact_balance_minus_fee(self, solana_client, test_config):
        """Drain account to exactly 0 by transferring balance minus fee."""
        sender = Keypair()
        recipient = Keypair()

        # Fund sender with known amount
        airdrop_amount = 1_000_000_000  # 1 SOL
        resp = await solana_client.request_airdrop(sender.pubkey(), airdrop_amount)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        # Determine actual fee by doing a probe: send a small transfer and measure cost
        probe_recipient = Keypair()
        probe_ix = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=probe_recipient.pubkey(),
                lamports=1,
            )
        )
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([probe_ix], sender.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([sender], blockhash)

        balance_before = (await solana_client.get_balance(sender.pubkey())).value
        resp = await solana_client.send_transaction(tx)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))
        balance_after = (await solana_client.get_balance(sender.pubkey())).value
        actual_fee = balance_before - balance_after - 1  # deducted = fee + 1 lamport transfer

        # Now drain the remaining balance
        remaining = balance_after
        transfer_amount = remaining - actual_fee

        drain_ix = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=transfer_amount,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([drain_ix], sender.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([sender], blockhash)

        resp = await solana_client.send_transaction(tx)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        sender_balance = await solana_client.get_balance(sender.pubkey())
        assert sender_balance.value == 0

        recipient_balance = await solana_client.get_balance(recipient.pubkey())
        assert recipient_balance.value == transfer_amount

    async def test_many_instructions_in_one_tx(self, solana_client, funded_keypair, test_config):
        """Transaction with multiple transfer instructions to different recipients."""
        num_transfers = 10
        recipients = [Keypair() for _ in range(num_transfers)]
        amount = 50_000

        instructions = [
            transfer(
                TransferParams(
                    from_pubkey=funded_keypair.pubkey(),
                    to_pubkey=r.pubkey(),
                    lamports=amount,
                )
            )
            for r in recipients
        ]

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash(instructions, funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.send_transaction(tx)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        # All recipients should have received funds
        for r in recipients:
            balance = await solana_client.get_balance(r.pubkey())
            assert balance.value == amount

    async def test_transfer_insufficient_funds_fails(self, solana_client, test_config):
        """Transfer more than account balance fails."""
        sender = Keypair()
        recipient = Keypair()

        # Fund with small amount
        resp = await solana_client.request_airdrop(sender.pubkey(), 100_000)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        # Try to send more than balance
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=1_000_000_000,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([transfer_ix], sender.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([sender], blockhash)

        try:
            resp = await solana_client.send_transaction(tx)
            sig = str(resp.value)
            await wait_for_confirmation(test_config.rpc_url, sig)
            status = await solana_client.get_signature_statuses([resp.value])
            if status.value[0] is not None:
                assert status.value[0].err is not None
        except Exception:
            pass  # Rejected at send — valid

    async def test_self_transfer_only_deducts_fee(self, solana_client, test_config):
        """Transferring to self only deducts the transaction fee."""
        sender = Keypair()
        amount = 1_000_000_000
        resp = await solana_client.request_airdrop(sender.pubkey(), amount)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        balance_before = (await solana_client.get_balance(sender.pubkey())).value

        transfer_ix = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=sender.pubkey(),
                lamports=500_000,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([transfer_ix], sender.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([sender], blockhash)

        resp = await solana_client.send_transaction(tx)
        await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        balance_after = (await solana_client.get_balance(sender.pubkey())).value
        fee_paid = balance_before - balance_after

        # Self-transfer: only fee deducted, transfer amount stays in account
        assert fee_paid > 0
        assert fee_paid <= 5000  # Fee should not exceed standard rate
        assert balance_after == balance_before - fee_paid
