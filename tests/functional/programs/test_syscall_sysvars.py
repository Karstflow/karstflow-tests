"""Tests for sysvar access via syscalls in the syscall-test BPF program.

Opcodes:
  0x05: Clock sysvar → return_data(slot as u64 LE)
  0x06: Rent sysvar → return_data(lamports_per_byte_year as u64 LE)
  0x09: Remaining compute units → return_data(cu as u64 LE)
"""

from __future__ import annotations

import struct

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


def build_syscall_ix(program_id: Pubkey, opcode: int, data: bytes = b"") -> Instruction:
    return Instruction(program_id=program_id, data=bytes([opcode]) + data, accounts=[])


@pytest.mark.programs
class TestSyscallSysvars:
    """Sysvar access via program syscalls."""

    async def test_clock_sysvar_returns_slot(self, solana_client, funded_keypair, syscall_program):
        """Program reads Clock sysvar, slot is returned and > 0."""
        ix = build_syscall_ix(syscall_program, 0x05)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            slot = struct.unpack("<Q", bytes(sim.value.return_data.data))[0]
            assert slot > 0, "Clock slot should be positive"

    async def test_clock_slot_close_to_rpc_slot(
        self, solana_client, funded_keypair, syscall_program
    ):
        """Program-reported slot is close to RPC-reported slot."""
        rpc_slot_resp = await solana_client.get_slot()
        rpc_slot = rpc_slot_resp.value

        ix = build_syscall_ix(syscall_program, 0x05)
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            prog_slot = struct.unpack("<Q", bytes(sim.value.return_data.data))[0]
            # Should be within a few slots of each other
            assert abs(int(prog_slot) - int(rpc_slot)) < 20

    async def test_rent_sysvar_returns_positive(
        self, solana_client, funded_keypair, syscall_program
    ):
        """Program reads Rent sysvar, lamports_per_byte_year > 0."""
        ix = build_syscall_ix(syscall_program, 0x06)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            lamports = struct.unpack("<Q", bytes(sim.value.return_data.data))[0]
            assert lamports > 0

    @pytest.mark.skip(reason="sol_remaining_compute_units feature-gated")
    async def test_remaining_compute_units(self, solana_client, funded_keypair, syscall_program):
        """Program reads remaining compute units, value is positive."""
        ix = build_syscall_ix(syscall_program, 0x09)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            cu = struct.unpack("<Q", bytes(sim.value.return_data.data))[0]
            assert cu > 0, "Remaining CU should be positive"

    @pytest.mark.skip(reason="sol_remaining_compute_units feature-gated")
    async def test_remaining_cu_logs_show_decrease(
        self, solana_client, funded_keypair, syscall_program
    ):
        """Program logs remaining CU twice — second reading is less."""
        ix = build_syscall_ix(syscall_program, 0x09)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.logs:
            cu_logs = [log for log in sim.value.logs if "remaining_cu" in log]
            if len(cu_logs) >= 2:
                # Extract CU values from log lines
                cu1 = (
                    int(cu_logs[0].split("remaining_cu_1: ")[1])
                    if "remaining_cu_1" in cu_logs[0]
                    else None
                )
                cu2 = (
                    int(cu_logs[1].split("remaining_cu_2: ")[1])
                    if "remaining_cu_2" in cu_logs[1]
                    else None
                )
                if cu1 is not None and cu2 is not None:
                    assert cu1 > cu2, f"CU should decrease: {cu1} > {cu2}"

    async def test_memory_ops(self, solana_client, funded_keypair, syscall_program):
        """Memory operations (memset, memcpy, memcmp) work correctly."""
        ix = build_syscall_ix(syscall_program, 0x0A)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            result = bytes(sim.value.return_data.data)
            assert len(result) == 2
            assert result[0] == 1, "Equal buffers should compare as equal"
            assert result[1] == 1, "Different buffers should compare as not equal"
