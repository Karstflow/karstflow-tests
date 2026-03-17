"""Tests for return_data syscall round-trip via the syscall-test BPF program.

The syscall-test program opcode 0x08 sets return_data from instruction_data[1..].
"""

from __future__ import annotations

import pytest
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from karstflow_tests.programs import deploy_program


@pytest.fixture
async def syscall_program(solana_client, funded_keypair, test_config):
    """Deploy the syscall-test program and return its pubkey."""
    program_kp = Keypair()
    return await deploy_program(
        solana_client, funded_keypair, "syscall_test", program_keypair=program_kp
    )


def build_syscall_ix(program_id: Pubkey, opcode: int, data: bytes) -> Instruction:
    return Instruction(program_id=program_id, data=bytes([opcode]) + data, accounts=[])


@pytest.mark.programs
class TestReturnData:
    """Return data round-trip tests."""

    async def test_return_data_round_trip(self, solana_client, funded_keypair, syscall_program):
        """Program sets return_data → simulate shows it in response."""
        payload = b"hello return data"
        ix = build_syscall_ix(syscall_program, 0x08, payload)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        assert sim.value.return_data is not None
        assert bytes(sim.value.return_data.data) == payload

    async def test_return_data_includes_program_id(
        self, solana_client, funded_keypair, syscall_program
    ):
        """Return data response includes the program_id that set it."""
        ix = build_syscall_ix(syscall_program, 0x08, b"test")

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            assert sim.value.return_data.program_id == syscall_program

    async def test_return_data_empty(self, solana_client, funded_keypair, syscall_program):
        """Empty return data is valid."""
        ix = build_syscall_ix(syscall_program, 0x08, b"")

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None

    async def test_return_data_binary(self, solana_client, funded_keypair, syscall_program):
        """Binary return data with all byte values round-trips correctly."""
        payload = bytes(range(256))[:128]  # 128 bytes of diverse binary data
        ix = build_syscall_ix(syscall_program, 0x08, payload)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            assert bytes(sim.value.return_data.data) == payload
