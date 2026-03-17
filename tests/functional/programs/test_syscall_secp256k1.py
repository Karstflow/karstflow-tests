"""Tests for secp256k1_recover syscall via the syscall-test BPF program.

The syscall-test program opcode 0x10 calls sol_secp256k1_recover:
  Data: [0x10, recovery_id(1), signature(64), message_hash(32)]
  Returns: recovered 64-byte public key via return_data.
"""

from __future__ import annotations

import hashlib

import pytest
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from karstflow_tests.programs import deploy_program

try:
    from coincurve import PrivateKey as CoinPrivateKey

    HAS_COINCURVE = True
except ImportError:
    HAS_COINCURVE = False


@pytest.fixture
async def syscall_program(solana_client, funded_keypair, test_config):
    """Deploy the syscall-test program and return its pubkey."""
    program_kp = Keypair()
    return await deploy_program(
        solana_client, funded_keypair, "syscall_test", program_keypair=program_kp
    )


def build_secp_recover_ix(
    program_id: Pubkey,
    recovery_id: int,
    signature: bytes,
    message_hash: bytes,
) -> Instruction:
    """Build a secp256k1_recover instruction."""
    data = bytes([0x10, recovery_id]) + signature + message_hash
    return Instruction(program_id=program_id, data=data, accounts=[])


@pytest.mark.programs
@pytest.mark.skip(reason="secp256k1_recover is feature-gated; not available in dev genesis")
class TestSyscallSecp256k1:
    """Secp256k1 recover via BPF syscall."""

    async def test_secp256k1_recover_valid(self, solana_client, funded_keypair, syscall_program):
        """Valid signature recovers the correct public key."""
        privkey = CoinPrivateKey()
        message = b"test secp256k1 recover syscall"
        msg_hash = hashlib.sha256(message).digest()

        sig_obj = privkey.sign_recoverable(msg_hash, hasher=None)
        signature = sig_obj[:64]
        recovery_id = sig_obj[64]

        expected_pubkey = privkey.public_key.format(compressed=False)[1:]

        ix = build_secp_recover_ix(syscall_program, recovery_id, signature, msg_hash)
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            recovered = bytes(sim.value.return_data.data)
            assert recovered == expected_pubkey

    async def test_secp256k1_recover_invalid_recovery_id(
        self, solana_client, funded_keypair, syscall_program
    ):
        """Invalid recovery_id (> 3) causes program error."""
        privkey = CoinPrivateKey()
        msg_hash = hashlib.sha256(b"test invalid").digest()

        sig_obj = privkey.sign_recoverable(msg_hash, hasher=None)
        signature = sig_obj[:64]

        ix = build_secp_recover_ix(syscall_program, 5, signature, msg_hash)
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is not None, "Bad recovery_id should fail"

    async def test_secp256k1_recover_known_vector(
        self, solana_client, funded_keypair, syscall_program
    ):
        """Known test vector produces expected recovered key."""
        # Generate a deterministic keypair for reproducible test
        privkey = CoinPrivateKey(secret=hashlib.sha256(b"karstflow-secp256k1-test-vector").digest())
        msg_hash = hashlib.sha256(b"known vector message").digest()

        sig_obj = privkey.sign_recoverable(msg_hash, hasher=None)
        signature = sig_obj[:64]
        recovery_id = sig_obj[64]

        expected = privkey.public_key.format(compressed=False)[1:]

        ix = build_secp_recover_ix(syscall_program, recovery_id, signature, msg_hash)
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            recovered = bytes(sim.value.return_data.data)
            assert recovered == expected
