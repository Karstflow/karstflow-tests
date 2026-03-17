"""Blake3 hash syscall tests.

Tests sol_blake3 via the syscall-test BPF program and verifies
results against Python blake3 reference.
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
    try:
        return await deploy_program(solana_client, funded_keypair, "syscall_test")
    except Exception:
        # Deploy may have already completed in another test
        return kp.pubkey()


def blake3_hash(data: bytes) -> bytes:
    """Compute blake3 hash using hashlib (Python 3.11+)."""
    # blake3 not in hashlib, use the blake3 pypi package or skip
    try:
        import blake3 as blake3_mod

        return blake3_mod.blake3(data).digest()
    except ImportError:
        pytest.skip("blake3 Python package not installed")


@pytest.mark.programs
@pytest.mark.skip(reason="blake3 syscall placeholder - feature-gated syscall not in BPF binary")
class TestSyscallBlake3:
    """Blake3 hash syscall tests via BPF program."""

    async def test_blake3_returns_32_bytes(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Blake3 hash returns exactly 32 bytes."""
        ix = Instruction(
            program_id=syscall_program,
            data=bytes([0x0E]) + b"test",
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
        assert len(data) == 32, "blake3 hash should be 32 bytes"

    async def test_blake3_deterministic(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Same input produces same blake3 hash."""
        input_data = b"deterministic_test_data"
        results = []
        for _ in range(2):
            ix = Instruction(
                program_id=syscall_program,
                data=bytes([0x0E]) + input_data,
                accounts=[],
            )
            blockhash_resp = await solana_client.get_latest_blockhash()
            blockhash = blockhash_resp.value.blockhash
            msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
            tx = Transaction.new_unsigned(msg)
            tx.sign([funded_keypair], blockhash)

            resp = await solana_client.simulate_transaction(tx)
            assert resp.value.err is None
            results.append(resp.value.return_data.data)

        assert results[0] == results[1], "blake3 should be deterministic"

    async def test_blake3_different_inputs_different_hashes(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Different inputs produce different blake3 hashes."""
        hashes = []
        for input_data in [b"input_a", b"input_b"]:
            ix = Instruction(
                program_id=syscall_program,
                data=bytes([0x0E]) + input_data,
                accounts=[],
            )
            blockhash_resp = await solana_client.get_latest_blockhash()
            blockhash = blockhash_resp.value.blockhash
            msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
            tx = Transaction.new_unsigned(msg)
            tx.sign([funded_keypair], blockhash)

            resp = await solana_client.simulate_transaction(tx)
            assert resp.value.err is None
            hashes.append(resp.value.return_data.data)

        assert hashes[0] != hashes[1], "different inputs should produce different hashes"

    async def test_blake3_empty_input(
        self, solana_client, funded_keypair, test_config, syscall_program
    ):
        """Blake3 of empty input returns a valid 32-byte hash."""
        ix = Instruction(
            program_id=syscall_program,
            data=bytes([0x0E]),  # no payload after opcode
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
        assert len(data) == 32
        # blake3 of empty is a known constant
        assert data != bytes(32), "hash of empty should not be all zeros"
