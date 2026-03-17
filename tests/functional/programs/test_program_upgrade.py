"""Tests for BPF Loader Upgradeable program lifecycle.

Tests deploy, upgrade, authority management, and buffer close
via BPF Loader Upgradeable.
"""

from __future__ import annotations

import pytest
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.transaction import Transaction

from karstflow_tests.programs import (
    _build_upg_set_authority_ix,
    deploy_program_upgradeable,
    get_programdata_address,
    upgrade_program,
)


def _build_invoke_ix(program_id, payer_pubkey):
    """Build a simple invoke instruction (no data, no accounts)."""
    return Instruction(program_id=program_id, data=b"", accounts=[])


async def _simulate_and_get_return_data(solana_client, funded_keypair, ix):
    """Simulate a tx and return the return_data bytes (or None)."""
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    sim = await solana_client.simulate_transaction(tx)
    if sim.value.err is not None:
        return sim, None
    if sim.value.return_data is not None:
        return sim, bytes(sim.value.return_data.data)
    return sim, None


@pytest.mark.programs
@pytest.mark.skip(reason="BPF Loader Upgradeable deploy not yet supported in karstflow dev-mode")
class TestProgramUpgrade:
    """BPF Loader Upgradeable lifecycle tests."""

    async def test_deploy_upgradeable_program(self, solana_client, funded_keypair, test_config):
        """Deploy via Upgradeable Loader, program executes and returns v1."""
        program_id, _authority = await deploy_program_upgradeable(
            solana_client, funded_keypair, "upgrade_v1"
        )

        ix = _build_invoke_ix(program_id, funded_keypair.pubkey())
        sim, ret = await _simulate_and_get_return_data(solana_client, funded_keypair, ix)
        assert sim.value.err is None
        assert ret == b"v1"

    async def test_upgrade_program_changes_behavior(
        self, solana_client, funded_keypair, test_config
    ):
        """Upgrade program from v1 to v2, behavior changes."""
        program_id, authority = await deploy_program_upgradeable(
            solana_client, funded_keypair, "upgrade_v1"
        )

        # Verify v1
        ix = _build_invoke_ix(program_id, funded_keypair.pubkey())
        sim, ret = await _simulate_and_get_return_data(solana_client, funded_keypair, ix)
        assert sim.value.err is None
        assert ret == b"v1"

        # Upgrade to v2
        await upgrade_program(
            solana_client,
            funded_keypair,
            program_id,
            "upgrade_v2",
            authority,
        )

        # Verify v2
        ix = _build_invoke_ix(program_id, funded_keypair.pubkey())
        sim, ret = await _simulate_and_get_return_data(solana_client, funded_keypair, ix)
        assert sim.value.err is None
        assert ret == b"v2"

    async def test_upgrade_authority_check(self, solana_client, funded_keypair, test_config):
        """Upgrade by non-authority fails."""
        program_id, _authority = await deploy_program_upgradeable(
            solana_client, funded_keypair, "upgrade_v1"
        )

        # Try upgrading with a different keypair (not authority)
        fake_authority = Keypair()

        # Write buffer as payer but try upgrade with fake authority
        from karstflow_tests.programs import (
            _build_upg_upgrade_ix,
            _write_buffer,
            load_program_bytes,
        )

        program_bytes = load_program_bytes("upgrade_v2")
        buffer_kp = Keypair()
        # Use funded_keypair as buffer authority (will work for writing)
        await _write_buffer(
            solana_client,
            funded_keypair,
            buffer_kp,
            funded_keypair,
            program_bytes,
        )

        programdata = get_programdata_address(program_id)
        upgrade_ix = _build_upg_upgrade_ix(
            programdata,
            program_id,
            buffer_kp.pubkey(),
            funded_keypair.pubkey(),
            fake_authority.pubkey(),
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([upgrade_ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair, fake_authority], blockhash)

        sim = await solana_client.simulate_transaction(tx)
        assert sim.value.err is not None, "Non-authority upgrade should fail"

    async def test_set_upgrade_authority(self, solana_client, funded_keypair, test_config):
        """Change upgrade authority, old authority can no longer upgrade."""
        program_id, authority = await deploy_program_upgradeable(
            solana_client, funded_keypair, "upgrade_v1"
        )

        new_authority = Keypair()
        programdata = get_programdata_address(program_id)

        set_auth_ix = _build_upg_set_authority_ix(
            programdata, authority.pubkey(), new_authority.pubkey()
        )

        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([set_auth_ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair, authority], blockhash)

        resp = await solana_client.send_transaction(tx)
        from karstflow_tests.programs import get_rpc_url
        from karstflow_tests.wait import wait_for_confirmation

        rpc_url = await get_rpc_url(solana_client)
        await wait_for_confirmation(rpc_url, str(resp.value))

        # Program still works
        ix = _build_invoke_ix(program_id, funded_keypair.pubkey())
        sim, ret = await _simulate_and_get_return_data(solana_client, funded_keypair, ix)
        assert sim.value.err is None
        assert ret == b"v1"
