"""Deep memory syscall tests.

Tests memmove (overlapping copy), large memset+memcpy+memcmp,
and pattern verification through the syscall-test BPF program.
"""

from __future__ import annotations

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
    return await deploy_program(solana_client, funded_keypair, "syscall_test")


@pytest.mark.programs
class TestSyscallMemoryDeep:
    """Deep memory operation tests via BPF program syscalls."""

    async def test_memmove_overlapping_copy(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Memmove with overlapping src/dst produces correct result."""
        ix = Instruction(
            program_id=syscall_program,
            data=bytes([0x0B]),
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
        data = bytes(return_data.data[0])
        assert data[0] == 1, "memmove overlapping copy should succeed"

    async def test_large_memops_round_trip(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Large (256-byte) memset+memcpy+memcmp round-trip."""
        ix = Instruction(
            program_id=syscall_program,
            data=bytes([0x0D]),
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
        data = bytes(return_data.data[0])
        assert data[0] == 1, "equal buffers should compare as equal"
        assert data[1] == 1, "modified buffer should compare as not equal"

    async def test_memops_basic_still_works(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Existing memset+memcpy+memcmp test (opcode 0x0A) still passes."""
        ix = Instruction(
            program_id=syscall_program,
            data=bytes([0x0A]),
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
        data = bytes(return_data.data[0])
        assert data[0] == 1, "equal buffers"
        assert data[1] == 1, "not-equal after modify"
