"""EpochSchedule sysvar syscall tests.

Tests sol_get_epoch_schedule_sysvar via the syscall-test BPF program
and verifies consistency with the RPC getEpochSchedule response.
"""

from __future__ import annotations

import struct

import pytest
from solders.instruction import Instruction
from solders.message import Message
from solders.transaction import Transaction

from karstflow_tests.programs import deploy_program


@pytest.fixture
async def syscall_program(solana_client, funded_keypair, test_config):
    """Deploy syscall-test program, or return existing if already deployed."""
    from karstflow_tests.programs import load_program_keypair
    kp = load_program_keypair("syscall_test")
    acct = await solana_client.get_account_info(kp.pubkey())
    if acct.value is not None and acct.value.executable:
        return kp.pubkey()
    try:
        return await deploy_program(solana_client, funded_keypair, "syscall_test")
    except Exception:
        # Deploy may have already completed in another test
        return kp.pubkey()


@pytest.mark.programs
class TestSyscallEpochSchedule:
    """EpochSchedule sysvar access via BPF syscall."""

    async def test_epoch_schedule_returns_slots_per_epoch(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Program reads EpochSchedule sysvar and returns slots_per_epoch."""
        ix = Instruction(
            program_id=syscall_program,
            data=bytes([0x07]),
            accounts=[],
        )
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.simulate_transaction(tx)
        assert resp.value.err is None

        return_data = resp.value.return_data
        assert return_data is not None
        data = return_data.data
        slots_per_epoch = struct.unpack("<Q", data[:8])[0]
        assert slots_per_epoch > 0, "slots_per_epoch must be positive"

    async def test_epoch_schedule_matches_rpc(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """slots_per_epoch from BPF syscall matches RPC getEpochSchedule."""
        # Get from RPC
        rpc_resp = await solana_client.get_epoch_schedule()
        rpc_slots_per_epoch = rpc_resp.value.slots_per_epoch

        # Get from BPF program
        ix = Instruction(
            program_id=syscall_program,
            data=bytes([0x07]),
            accounts=[],
        )
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.simulate_transaction(tx)
        assert resp.value.err is None

        return_data = resp.value.return_data
        data = return_data.data
        bpf_slots_per_epoch = struct.unpack("<Q", data[:8])[0]

        assert bpf_slots_per_epoch == rpc_slots_per_epoch

    async def test_epoch_schedule_logs_contain_values(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Program logs contain epoch_schedule field values."""
        ix = Instruction(
            program_id=syscall_program,
            data=bytes([0x07]),
            accounts=[],
        )
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.simulate_transaction(tx)
        assert resp.value.err is None

        logs = resp.value.logs or []
        epoch_log = [line for line in logs if "epoch_schedule:" in line]
        assert len(epoch_log) > 0, "should have epoch_schedule log line"
        assert "slots_per_epoch=" in epoch_log[0]
        assert "warmup=" in epoch_log[0]
