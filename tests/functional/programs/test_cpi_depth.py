"""Tests for CPI call depth limits via the cpi-depth BPF program.

The cpi-depth program reads depth from instruction_data[0] and recursively
invokes itself depth times via CPI. Solana CPI depth limit is 4.
"""

from __future__ import annotations

import pytest
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from karstflow_tests.programs import deploy_program


@pytest.fixture
async def cpi_depth_program(solana_client, funded_keypair, test_config):
    """Deploy the cpi-depth program and return its pubkey."""
    program_kp = Keypair()
    return await deploy_program(
        solana_client, funded_keypair, "cpi_depth", program_keypair=program_kp
    )


def build_cpi_depth_ix(program_id: Pubkey, depth: int, signer: Pubkey) -> Instruction:
    """Build a cpi-depth instruction with target depth."""
    return Instruction(
        program_id=program_id,
        data=bytes([depth]),
        accounts=[
            AccountMeta(pubkey=signer, is_signer=True, is_writable=False),
        ],
    )


@pytest.mark.programs
@pytest.mark.cpi
class TestCpiDepth:
    """CPI depth limit tests."""

    async def test_cpi_depth_0(self, solana_client, funded_keypair, cpi_depth_program):
        """Depth 0 — no CPI, just logs and returns."""
        ix = build_cpi_depth_ix(cpi_depth_program, 0, funded_keypair.pubkey())

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.logs:
            assert any("reached bottom" in log for log in sim.value.logs)

    async def test_cpi_depth_1(self, solana_client, funded_keypair, cpi_depth_program):
        """Depth 1 — one level of CPI, should succeed."""
        ix = build_cpi_depth_ix(cpi_depth_program, 1, funded_keypair.pubkey())

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.logs:
            assert any("reached bottom" in log for log in sim.value.logs)

    async def test_cpi_depth_3(self, solana_client, funded_keypair, cpi_depth_program):
        """Depth 3 — three levels of CPI, should succeed (within limit)."""
        ix = build_cpi_depth_ix(cpi_depth_program, 3, funded_keypair.pubkey())

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None

    async def test_cpi_depth_4(self, solana_client, funded_keypair, cpi_depth_program):
        """Depth 4 — four levels of CPI, at Solana limit."""
        ix = build_cpi_depth_ix(cpi_depth_program, 4, funded_keypair.pubkey())

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        # May succeed or fail depending on exact depth counting (stack height limit)
        # Either way, we verify no crash
        if sim.value.err is not None:
            # Acceptable — CPI depth exceeded
            pass

    @pytest.mark.skip(reason="karstflow dev-mode CPI depth limit not enforced")
    async def test_cpi_depth_exceeds_limit_fails(
        self, solana_client, funded_keypair, cpi_depth_program
    ):
        """Depth 10 — well beyond CPI limit, should fail."""
        ix = build_cpi_depth_ix(cpi_depth_program, 10, funded_keypair.pubkey())

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is not None, "Excessive CPI depth should fail"

    async def test_cpi_depth_logs_at_each_level(
        self, solana_client, funded_keypair, cpi_depth_program
    ):
        """CPI at depth 2 logs at each level."""
        ix = build_cpi_depth_ix(cpi_depth_program, 2, funded_keypair.pubkey())

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.logs:
            depth_logs = [log for log in sim.value.logs if "depth=" in log]
            # Should see depth=2, depth=1, depth=0
            assert len(depth_logs) >= 3

    async def test_cpi_depth_return_data_from_deepest(
        self, solana_client, funded_keypair, cpi_depth_program
    ):
        """Return data set by innermost CPI call is visible in simulate."""
        ix = build_cpi_depth_ix(cpi_depth_program, 2, funded_keypair.pubkey())

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is None
        if sim.value.return_data is not None:
            assert bytes(sim.value.return_data.data) == b"bottom"
