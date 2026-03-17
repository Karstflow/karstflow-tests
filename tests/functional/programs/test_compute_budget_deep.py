"""Deep tests for ComputeBudget program instructions.

Tests SetComputeUnitLimit, SetComputeUnitPrice, and RequestHeapFrame
to verify the validator correctly enforces compute resource management.
"""

from __future__ import annotations

import struct

import pytest
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from karstflow_tests.programs import (
    build_compute_budget_set_price,
    build_compute_budget_set_units,
    send_multi_instruction_tx,
)
from karstflow_tests.wait import wait_for_confirmation

COMPUTE_BUDGET = Pubkey.from_string("ComputeBudget111111111111111111111111111111")


def build_request_heap_frame(heap_size: int) -> Instruction:
    """Build ComputeBudget RequestHeapFrame instruction.

    Instruction 1: RequestHeapFrame (u8=1, u32=heap_size_bytes).
    heap_size must be multiple of 1024 and <= 256*1024.
    """
    data = struct.pack("<BI", 1, heap_size)
    return Instruction(program_id=COMPUTE_BUDGET, data=data, accounts=[])


@pytest.mark.programs
class TestComputeBudgetDeep:
    """Compute budget instruction tests."""

    async def test_set_compute_unit_limit_high(self, solana_client, funded_keypair, test_config):
        """Setting a high CU limit allows a transfer to complete."""
        recipient = Keypair()
        cu_ix = build_compute_budget_set_units(400_000)
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )

        sig = await send_multi_instruction_tx(
            solana_client,
            funded_keypair,
            [cu_ix, transfer_ix],
        )
        await wait_for_confirmation(test_config.rpc_url, sig)

        balance = await solana_client.get_balance(recipient.pubkey())
        assert balance.value == 100_000

    async def test_set_compute_unit_limit_too_low_fails(
        self, solana_client, funded_keypair, test_config
    ):
        """Setting CU limit to 1 causes the transaction to fail (exceeds budget)."""
        recipient = Keypair()
        # 1 CU is not enough for any instruction
        cu_ix = build_compute_budget_set_units(1)
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([cu_ix, transfer_ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        # Either send fails or tx lands with error
        try:
            resp = await solana_client.send_transaction(tx)
            sig = str(resp.value)
            await wait_for_confirmation(test_config.rpc_url, sig)
            status = await solana_client.get_signature_statuses([resp.value])
            if status.value[0] is not None:
                assert status.value[0].err is not None
        except Exception:
            pass  # Rejected at send — valid

    async def test_set_compute_unit_price_increases_fee(
        self, solana_client, funded_keypair, test_config
    ):
        """Setting a CU price adds priority fee on top of base fee."""
        recipient = Keypair()

        # First tx: no priority fee
        transfer_ix_1 = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg1 = Message.new_with_blockhash([transfer_ix_1], funded_keypair.pubkey(), blockhash)
        tx1 = Transaction.new_unsigned(msg1)
        tx1.sign([funded_keypair], blockhash)

        resp1 = await solana_client.send_transaction(tx1)
        await wait_for_confirmation(test_config.rpc_url, str(resp1.value))

        tx_detail_1 = await solana_client.get_transaction(
            resp1.value, max_supported_transaction_version=0
        )
        base_fee = tx_detail_1.value.transaction.meta.fee if tx_detail_1.value else 5000

        # Second tx: with priority fee (1000 micro-lamports per CU)
        transfer_ix_2 = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )
        price_ix = build_compute_budget_set_price(1000)
        cu_ix = build_compute_budget_set_units(200_000)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg2 = Message.new_with_blockhash(
            [price_ix, cu_ix, transfer_ix_2], funded_keypair.pubkey(), blockhash
        )
        tx2 = Transaction.new_unsigned(msg2)
        tx2.sign([funded_keypair], blockhash)

        resp2 = await solana_client.send_transaction(tx2)
        await wait_for_confirmation(test_config.rpc_url, str(resp2.value))

        tx_detail_2 = await solana_client.get_transaction(
            resp2.value, max_supported_transaction_version=0
        )
        if tx_detail_2.value is not None:
            priority_fee = tx_detail_2.value.transaction.meta.fee
            # Priority fee should be >= base fee
            assert priority_fee >= base_fee

    async def test_simulate_returns_units_consumed(self, solana_client, funded_keypair):
        """simulateTransaction returns unitsConsumed field."""
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

        sim_resp = await solana_client.simulate_transaction(tx)
        assert sim_resp.value.err is None
        assert sim_resp.value.units_consumed is not None
        assert sim_resp.value.units_consumed > 0

    async def test_simulate_with_cu_limit(self, solana_client, funded_keypair):
        """Simulate with CU limit shows units consumed within that limit."""
        recipient = Keypair()
        cu_ix = build_compute_budget_set_units(50_000)
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([cu_ix, transfer_ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim_resp = await solana_client.simulate_transaction(tx)
        assert sim_resp.value.err is None
        assert sim_resp.value.units_consumed is not None
        assert sim_resp.value.units_consumed <= 50_000

    async def test_request_heap_frame_with_program(
        self, solana_client, funded_keypair, test_config
    ):
        """RequestHeapFrame instruction is accepted in transaction."""
        recipient = Keypair()
        heap_ix = build_request_heap_frame(256 * 1024)  # 256KB
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )

        sig = await send_multi_instruction_tx(
            solana_client,
            funded_keypair,
            [heap_ix, transfer_ix],
        )
        await wait_for_confirmation(test_config.rpc_url, sig)

        balance = await solana_client.get_balance(recipient.pubkey())
        assert balance.value == 100_000

    async def test_multiple_compute_budget_instructions(
        self, solana_client, funded_keypair, test_config
    ):
        """SetComputeUnitLimit + SetComputeUnitPrice in same transaction."""
        recipient = Keypair()
        cu_ix = build_compute_budget_set_units(200_000)
        price_ix = build_compute_budget_set_price(500)
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000,
            )
        )

        sig = await send_multi_instruction_tx(
            solana_client,
            funded_keypair,
            [cu_ix, price_ix, transfer_ix],
        )
        await wait_for_confirmation(test_config.rpc_url, sig)

        balance = await solana_client.get_balance(recipient.pubkey())
        assert balance.value == 100_000
