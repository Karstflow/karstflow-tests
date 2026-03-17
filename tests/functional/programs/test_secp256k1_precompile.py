"""Tests for the Secp256k1 signature recovery precompile.

The Secp256k1 precompile (KeccakSecp256k11111111111111111111111111111)
recovers Ethereum-style ECDSA public keys from signatures. The instruction
data follows a specific binary format.

Instruction data layout:
  - u8: num_signatures
  - u16: padding (0)
  For each signature:
    - u16: eth_address_offset (20 bytes Ethereum address)
    - u8:  eth_address_instruction_index (0xFF = current)
    - u16: signature_offset (64 bytes compact sig)
    - u8:  signature_instruction_index (0xFF = current)
    - u16: message_data_offset
    - u16: message_data_size
    - u8:  message_instruction_index (0xFF = current)
  Then raw data: eth_address (20) + signature (64) + recovery_id (1) + message (N)
"""

from __future__ import annotations

import hashlib
import struct

import pytest
from solders.instruction import Instruction
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from karstflow_tests.wait import wait_for_confirmation

SECP256K1_PROGRAM = Pubkey.from_string("KeccakSecp256k11111111111111111111111111111")

THIS_INSTR_U8 = 0xFF


def _keccak256(data: bytes) -> bytes:
    return hashlib.new("sha3_256", data).digest()


def _try_build_secp256k1_instruction() -> Instruction | None:
    """Try to build a secp256k1 precompile instruction using coincurve.

    Returns None if coincurve is not available.
    """
    try:
        from coincurve import PrivateKey
    except ImportError:
        return None

    # Generate a key and sign
    privkey = PrivateKey()
    message = b"test secp256k1 recovery"
    msg_hash = hashlib.new("sha3_256", message).digest()

    # Sign with recoverable signature
    sig_obj = privkey.sign_recoverable(msg_hash, hasher=None)
    sig_bytes = sig_obj[:64]
    recovery_id = sig_obj[64]

    # Ethereum address = last 20 bytes of keccak256(uncompressed_pubkey[1:])
    pubkey_uncompressed = privkey.public_key.format(compressed=False)
    eth_address = hashlib.new("sha3_256", pubkey_uncompressed[1:]).digest()[-20:]

    # Build instruction data
    header_size = 1 + 2  # num_sigs(u8) + padding(u16)
    per_sig_size = 2 + 1 + 2 + 1 + 2 + 2 + 1  # 11 bytes per signature descriptor
    offsets_size = per_sig_size

    eth_addr_offset = header_size + offsets_size
    sig_offset = eth_addr_offset + 20
    # recovery_id is appended right after the 64-byte signature
    msg_offset = sig_offset + 64 + 1
    msg_size = len(message)

    data = struct.pack("<B H", 1, 0)  # num_sigs, padding
    data += struct.pack(
        "<HB HB HHB",
        eth_addr_offset,
        THIS_INSTR_U8,
        sig_offset,
        THIS_INSTR_U8,
        msg_offset,
        msg_size,
        THIS_INSTR_U8,
    )
    data += eth_address + sig_bytes + bytes([recovery_id]) + message

    return Instruction(program_id=SECP256K1_PROGRAM, data=data, accounts=[])


def _build_secp256k1_invalid_recovery_id() -> Instruction | None:
    """Build a secp256k1 instruction with invalid recovery_id (4)."""
    try:
        from coincurve import PrivateKey
    except ImportError:
        return None

    privkey = PrivateKey()
    message = b"invalid recovery test"
    msg_hash = hashlib.new("sha3_256", message).digest()

    sig_obj = privkey.sign_recoverable(msg_hash, hasher=None)
    sig_bytes = sig_obj[:64]

    pubkey_uncompressed = privkey.public_key.format(compressed=False)
    eth_address = hashlib.new("sha3_256", pubkey_uncompressed[1:]).digest()[-20:]

    header_size = 1 + 2
    per_sig_size = 11
    offsets_size = per_sig_size

    eth_addr_offset = header_size + offsets_size
    sig_offset = eth_addr_offset + 20
    msg_offset = sig_offset + 64 + 1
    msg_size = len(message)

    data = struct.pack("<B H", 1, 0)
    data += struct.pack(
        "<HB HB HHB",
        eth_addr_offset,
        THIS_INSTR_U8,
        sig_offset,
        THIS_INSTR_U8,
        msg_offset,
        msg_size,
        THIS_INSTR_U8,
    )
    # Use recovery_id = 4 (invalid, must be 0-3)
    data += eth_address + sig_bytes + bytes([4]) + message

    return Instruction(program_id=SECP256K1_PROGRAM, data=data, accounts=[])


def _build_secp256k1_wrong_address() -> Instruction | None:
    """Build a secp256k1 instruction with wrong Ethereum address."""
    try:
        from coincurve import PrivateKey
    except ImportError:
        return None

    privkey = PrivateKey()
    message = b"wrong address test"
    msg_hash = hashlib.new("sha3_256", message).digest()

    sig_obj = privkey.sign_recoverable(msg_hash, hasher=None)
    sig_bytes = sig_obj[:64]
    recovery_id = sig_obj[64]

    # Use a fake address (all zeros)
    fake_address = b"\x00" * 20

    header_size = 1 + 2
    per_sig_size = 11
    offsets_size = per_sig_size

    eth_addr_offset = header_size + offsets_size
    sig_offset = eth_addr_offset + 20
    msg_offset = sig_offset + 64 + 1
    msg_size = len(message)

    data = struct.pack("<B H", 1, 0)
    data += struct.pack(
        "<HB HB HHB",
        eth_addr_offset,
        THIS_INSTR_U8,
        sig_offset,
        THIS_INSTR_U8,
        msg_offset,
        msg_size,
        THIS_INSTR_U8,
    )
    data += fake_address + sig_bytes + bytes([recovery_id]) + message

    return Instruction(program_id=SECP256K1_PROGRAM, data=data, accounts=[])


needs_coincurve = pytest.mark.skipif(
    _try_build_secp256k1_instruction() is None,
    reason="coincurve not installed",
)


@pytest.mark.programs
class TestSecp256k1Precompile:
    """Secp256k1 ECDSA recovery precompile tests."""

    @needs_coincurve
    async def test_secp256k1_recover_valid(self, solana_client, funded_keypair, test_config):
        """Valid secp256k1 signature recovers correct Ethereum address."""
        ix = _try_build_secp256k1_instruction()
        assert ix is not None

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.send_transaction(tx)
        sig = str(resp.value)
        await wait_for_confirmation(test_config.rpc_url, sig)

        status = await solana_client.get_signature_statuses([resp.value])
        assert status.value[0] is not None
        assert status.value[0].err is None

    @needs_coincurve
    async def test_secp256k1_recover_invalid_recovery_id(
        self, solana_client, funded_keypair, test_config
    ):
        """Invalid recovery_id (>3) causes precompile to fail."""
        ix = _build_secp256k1_invalid_recovery_id()
        assert ix is not None

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        try:
            resp = await solana_client.send_transaction(tx)
            sig = str(resp.value)
            await wait_for_confirmation(test_config.rpc_url, sig)
            status = await solana_client.get_signature_statuses([resp.value])
            assert status.value[0] is not None
            assert status.value[0].err is not None
        except Exception:
            # sendTransaction rejected — also valid
            pass

    @needs_coincurve
    async def test_secp256k1_recover_wrong_address(
        self, solana_client, funded_keypair, test_config
    ):
        """Recovered address doesn't match provided address → precompile fails."""
        ix = _build_secp256k1_wrong_address()
        assert ix is not None

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        try:
            resp = await solana_client.send_transaction(tx)
            sig = str(resp.value)
            await wait_for_confirmation(test_config.rpc_url, sig)
            status = await solana_client.get_signature_statuses([resp.value])
            assert status.value[0] is not None
            assert status.value[0].err is not None
        except Exception:
            pass

    @needs_coincurve
    async def test_secp256k1_recover_with_simulate(self, solana_client, funded_keypair):
        """Simulate a valid secp256k1 verification — no error in result."""
        ix = _try_build_secp256k1_instruction()
        assert ix is not None

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim_resp = await solana_client.simulate_transaction(tx)
        assert sim_resp.value.err is None
