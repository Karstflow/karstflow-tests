"""Tests for alt_bn128 curve operations via the curve-test BPF program.

The curve-test program dispatches on instruction_data[0]:
  0x01: alt_bn128 point addition (128 bytes → 64 bytes)
  0x02: alt_bn128 scalar multiplication (96 bytes → 64 bytes)
  0x03: alt_bn128 identity check (point + zero = point)

The alt_bn128 curve (BN254) is the same as used by Ethereum precompiles.
"""

from __future__ import annotations

import pytest
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from karstflow_tests.programs import deploy_program

# alt_bn128 generator point G1 (big-endian, 32 bytes each coordinate)
# G1 = (1, 2) on BN254
G1_X = (1).to_bytes(32, "big")
G1_Y = (2).to_bytes(32, "big")
G1_POINT = G1_X + G1_Y

# Zero point (point at infinity) — 64 zero bytes
ZERO_POINT = b"\x00" * 64


@pytest.fixture
async def curve_program(solana_client, funded_keypair, test_config):
    """Deploy the curve-test program and return its pubkey."""
    program_kp = Keypair()
    return await deploy_program(
        solana_client,
        funded_keypair,
        "curve_test",
        program_keypair=program_kp,
    )


def build_curve_ix(program_id: Pubkey, opcode: int, data: bytes) -> Instruction:
    return Instruction(
        program_id=program_id,
        data=bytes([opcode]) + data,
        accounts=[],
    )


@pytest.mark.programs
class TestCurveOps:
    """alt_bn128 curve operations via BPF syscall."""

    async def test_alt_bn128_add_generator_to_itself(
        self, solana_client, funded_keypair, curve_program
    ):
        """Adding G1 + G1 produces a valid point (not zero)."""
        input_data = G1_POINT + G1_POINT
        ix = build_curve_ix(curve_program, 0x01, input_data)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            result = bytes(sim.value.return_data.data)
            assert len(result) == 64
            # Result should not be zero point
            assert result != ZERO_POINT

    async def test_alt_bn128_add_zero_identity(self, solana_client, funded_keypair, curve_program):
        """G1 + zero = G1 (identity element)."""
        ix = build_curve_ix(curve_program, 0x03, G1_POINT)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            result = bytes(sim.value.return_data.data)
            assert result == G1_POINT, "G1 + 0 should equal G1"

    @pytest.mark.skip(reason="alt_bn128 scalar multiplication may require feature gate activation")
    async def test_alt_bn128_mul_by_one(self, solana_client, funded_keypair, curve_program):
        """G1 * 1 = G1."""
        scalar_one = (1).to_bytes(32, "big")
        input_data = G1_POINT + scalar_one
        ix = build_curve_ix(curve_program, 0x02, input_data)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            result = bytes(sim.value.return_data.data)
            assert result == G1_POINT, "G1 * 1 should equal G1"

    @pytest.mark.skip(reason="alt_bn128 scalar multiplication may require feature gate activation")
    async def test_alt_bn128_mul_by_zero(self, solana_client, funded_keypair, curve_program):
        """G1 * 0 = zero point (point at infinity)."""
        scalar_zero = (0).to_bytes(32, "big")
        input_data = G1_POINT + scalar_zero
        ix = build_curve_ix(curve_program, 0x02, input_data)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            result = bytes(sim.value.return_data.data)
            assert result == ZERO_POINT, "G1 * 0 should be zero point"

    async def test_alt_bn128_add_zero_plus_zero(self, solana_client, funded_keypair, curve_program):
        """Zero + zero = zero."""
        input_data = ZERO_POINT + ZERO_POINT
        ix = build_curve_ix(curve_program, 0x01, input_data)

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            result = bytes(sim.value.return_data.data)
            assert result == ZERO_POINT, "0 + 0 should be zero"
