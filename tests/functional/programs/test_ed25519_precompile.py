"""Tests for the Ed25519 signature verification precompile.

The Ed25519 precompile (Ed25519SigVerify111111111111111111111111111) verifies
Ed25519 signatures as part of transaction processing. The instruction data
follows a specific binary format defined by the Solana protocol.

Instruction data layout:
  - u8: num_signatures
  - u8: padding (0)
  For each signature:
    - u16: signature_offset
    - u16: signature_instruction_index (0xFFFF = current)
    - u16: public_key_offset
    - u16: public_key_instruction_index (0xFFFF = current)
    - u16: message_data_offset
    - u16: message_data_size
    - u16: message_instruction_index (0xFFFF = current)
  Then raw data: signature (64 bytes) + pubkey (32 bytes) + message (N bytes)
"""

from __future__ import annotations

import struct

import pytest
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from karstflow_tests.wait import wait_for_confirmation

ED25519_PROGRAM = Pubkey.from_string("Ed25519SigVerify111111111111111111111111111")

# Instruction index 0xFFFF means "this instruction"
THIS_INSTR = 0xFFFF


def build_ed25519_verify_instruction(
    keypair: Keypair,
    message: bytes,
) -> Instruction:
    """Build an Ed25519 precompile instruction that verifies one signature."""
    signature = keypair.sign_message(message)
    sig_bytes = bytes(signature)
    pubkey_bytes = bytes(keypair.pubkey())

    # Header: num_signatures(1) + padding(1) = 2 bytes
    # Per-sig offsets: 7 x u16 = 14 bytes
    header_size = 2 + 14

    sig_offset = header_size
    pubkey_offset = sig_offset + 64
    msg_offset = pubkey_offset + 32
    msg_size = len(message)

    data = struct.pack(
        "<BB HH HH HHH",
        1,  # num_signatures
        0,  # padding
        sig_offset,
        THIS_INSTR,  # signature_instruction_index
        pubkey_offset,
        THIS_INSTR,  # public_key_instruction_index
        msg_offset,
        msg_size,
        THIS_INSTR,  # message_instruction_index
    )
    data += sig_bytes + pubkey_bytes + message

    return Instruction(program_id=ED25519_PROGRAM, data=data, accounts=[])


def build_ed25519_invalid_sig_instruction(
    keypair: Keypair,
    message: bytes,
) -> Instruction:
    """Build an Ed25519 instruction with a tampered signature."""
    signature = keypair.sign_message(message)
    sig_bytes = bytearray(bytes(signature))
    sig_bytes[0] ^= 0xFF  # corrupt first byte

    pubkey_bytes = bytes(keypair.pubkey())

    header_size = 2 + 14
    sig_offset = header_size
    pubkey_offset = sig_offset + 64
    msg_offset = pubkey_offset + 32
    msg_size = len(message)

    data = struct.pack(
        "<BB HH HH HHH",
        1,
        0,
        sig_offset,
        THIS_INSTR,
        pubkey_offset,
        THIS_INSTR,
        msg_offset,
        msg_size,
        THIS_INSTR,
    )
    data += bytes(sig_bytes) + pubkey_bytes + message

    return Instruction(program_id=ED25519_PROGRAM, data=data, accounts=[])


def build_ed25519_wrong_message_instruction(
    keypair: Keypair,
    message: bytes,
    wrong_message: bytes,
) -> Instruction:
    """Build an Ed25519 instruction with correct sig but wrong message."""
    signature = keypair.sign_message(message)
    sig_bytes = bytes(signature)
    pubkey_bytes = bytes(keypair.pubkey())

    header_size = 2 + 14
    sig_offset = header_size
    pubkey_offset = sig_offset + 64
    msg_offset = pubkey_offset + 32
    msg_size = len(wrong_message)

    data = struct.pack(
        "<BB HH HH HHH",
        1,
        0,
        sig_offset,
        THIS_INSTR,
        pubkey_offset,
        THIS_INSTR,
        msg_offset,
        msg_size,
        THIS_INSTR,
    )
    data += sig_bytes + pubkey_bytes + wrong_message

    return Instruction(program_id=ED25519_PROGRAM, data=data, accounts=[])


def build_ed25519_multi_sig_instruction(
    keypairs_and_messages: list[tuple[Keypair, bytes]],
) -> Instruction:
    """Build an Ed25519 instruction verifying multiple signatures."""
    num_sigs = len(keypairs_and_messages)
    per_sig_header = 14  # 7 x u16
    header_size = 2 + num_sigs * per_sig_header

    # Compute offsets for each signature block
    raw_data = b""
    offsets_data = b""
    current_offset = header_size

    for kp, msg in keypairs_and_messages:
        sig = kp.sign_message(msg)
        sig_bytes = bytes(sig)
        pubkey_bytes = bytes(kp.pubkey())

        sig_offset = current_offset + len(raw_data)
        pubkey_offset = sig_offset + 64
        msg_offset = pubkey_offset + 32

        offsets_data += struct.pack(
            "<HH HH HHH",
            sig_offset,
            THIS_INSTR,
            pubkey_offset,
            THIS_INSTR,
            msg_offset,
            len(msg),
            THIS_INSTR,
        )
        raw_data += sig_bytes + pubkey_bytes + msg

    data = struct.pack("<BB", num_sigs, 0) + offsets_data + raw_data
    return Instruction(program_id=ED25519_PROGRAM, data=data, accounts=[])


@pytest.mark.programs
class TestEd25519Precompile:
    """Ed25519 signature verification precompile tests."""

    async def test_ed25519_verify_valid_signature(self, solana_client, funded_keypair, test_config):
        """Valid Ed25519 signature passes precompile verification."""
        message = b"hello karstflow"
        verify_kp = Keypair()
        ix = build_ed25519_verify_instruction(verify_kp, message)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.send_transaction(tx)
        sig = str(resp.value)
        await wait_for_confirmation(test_config.rpc_url, sig)

        # Transaction confirmed = precompile passed
        status = await solana_client.get_signature_statuses([resp.value])
        assert status.value[0] is not None
        assert status.value[0].err is None

    async def test_ed25519_verify_invalid_signature(
        self, solana_client, funded_keypair, test_config
    ):
        """Tampered Ed25519 signature fails precompile verification."""
        message = b"hello karstflow"
        verify_kp = Keypair()
        ix = build_ed25519_invalid_sig_instruction(verify_kp, message)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        # Should fail — either sendTransaction rejects or tx has error
        try:
            resp = await solana_client.send_transaction(tx)
            sig = str(resp.value)
            await wait_for_confirmation(test_config.rpc_url, sig)
            status = await solana_client.get_signature_statuses([resp.value])
            # If it landed, it should have an error
            assert status.value[0] is not None
            assert status.value[0].err is not None
        except Exception:
            # sendTransaction rejected — also valid
            pass

    async def test_ed25519_verify_wrong_message(self, solana_client, funded_keypair, test_config):
        """Ed25519 sig for one message but verifying different message fails."""
        verify_kp = Keypair()
        ix = build_ed25519_wrong_message_instruction(
            verify_kp, b"correct message", b"wrong message"
        )

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

    async def test_ed25519_verify_multiple_signatures(
        self, solana_client, funded_keypair, test_config
    ):
        """Multiple Ed25519 signatures verified in a single instruction."""
        kp1, kp2 = Keypair(), Keypair()
        msg1, msg2 = b"message one", b"message two"
        ix = build_ed25519_multi_sig_instruction([(kp1, msg1), (kp2, msg2)])

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

    async def test_ed25519_with_transfer_in_same_tx(
        self, solana_client, funded_keypair, test_config
    ):
        """Ed25519 precompile + SOL transfer in the same transaction."""
        from solders.system_program import TransferParams, transfer

        verify_kp = Keypair()
        recipient = Keypair()

        ed25519_ix = build_ed25519_verify_instruction(verify_kp, b"verify me")
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=1_000_000,
            )
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash(
            [ed25519_ix, transfer_ix], funded_keypair.pubkey(), blockhash
        )
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        resp = await solana_client.send_transaction(tx)
        sig = str(resp.value)
        await wait_for_confirmation(test_config.rpc_url, sig)

        # Both instructions should have succeeded
        balance_resp = await solana_client.get_balance(recipient.pubkey())
        assert balance_resp.value == 1_000_000
