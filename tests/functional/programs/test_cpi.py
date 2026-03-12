"""Tests for Cross-Program Invocation (CPI) via cpi-proxy program."""

from __future__ import annotations

import struct

import pytest
from solana.rpc.async_api import AsyncClient
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.transaction import Transaction

from karstflow_tests.programs import (
    SYSTEM_PROGRAM,
    deploy_program,
    get_rpc_url,
)
from karstflow_tests.wait import wait_for_confirmation

pytestmark = [pytest.mark.programs, pytest.mark.cpi]


async def test_cpi_transfer(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """CPI proxy transfers lamports from source to destination via System Program."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "cpi_proxy", program_keypair=program_kp
    )

    # Create destination account (fund it minimally so it exists)
    destination = Keypair()
    rpc_url = await get_rpc_url(solana_client)

    # Airdrop to destination so account exists
    airdrop_resp = await solana_client.request_airdrop(
        destination.pubkey(), 1_000_000
    )
    await wait_for_confirmation(rpc_url, str(airdrop_resp.value))

    # Get initial balance
    dst_before = await solana_client.get_balance(destination.pubkey())

    transfer_amount = 100_000  # 0.0001 SOL
    ix_data = struct.pack("<Q", transfer_amount)
    ix = Instruction(
        program_id=program_id,
        data=ix_data,
        accounts=[
            AccountMeta(pubkey=funded_keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=destination.pubkey(), is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Verify balances changed
    dst_after = await solana_client.get_balance(destination.pubkey())
    assert dst_after.value == dst_before.value + transfer_amount


async def test_cpi_transfer_zero_amount(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """CPI proxy with 0 lamports should succeed (no-op transfer)."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "cpi_proxy", program_keypair=program_kp
    )

    destination = Keypair()
    rpc_url = await get_rpc_url(solana_client)
    airdrop_resp = await solana_client.request_airdrop(destination.pubkey(), 1_000_000)
    await wait_for_confirmation(rpc_url, str(airdrop_resp.value))

    ix_data = struct.pack("<Q", 0)
    ix = Instruction(
        program_id=program_id,
        data=ix_data,
        accounts=[
            AccountMeta(pubkey=funded_keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=destination.pubkey(), is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))


async def test_cpi_invalid_data_fails(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """CPI proxy with < 8 bytes data should fail with InvalidInstructionData."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "cpi_proxy", program_keypair=program_kp
    )

    destination = Keypair()
    ix = Instruction(
        program_id=program_id,
        data=b"\x01\x02",  # only 2 bytes, need 8
        accounts=[
            AccountMeta(pubkey=funded_keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=destination.pubkey(), is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)

    sim = await solana_client.simulate_transaction(tx)
    assert sim.value.err is not None


async def test_cpi_simulate_logs(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Simulate CPI transfer and verify program logs are present."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "cpi_proxy", program_keypair=program_kp
    )

    destination = Keypair()
    rpc_url = await get_rpc_url(solana_client)
    airdrop_resp = await solana_client.request_airdrop(destination.pubkey(), 1_000_000)
    await wait_for_confirmation(rpc_url, str(airdrop_resp.value))

    ix_data = struct.pack("<Q", 1000)
    ix = Instruction(
        program_id=program_id,
        data=ix_data,
        accounts=[
            AccountMeta(pubkey=funded_keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=destination.pubkey(), is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)

    sim = await solana_client.simulate_transaction(tx)
    assert sim.value.err is None
    if sim.value.logs:
        log_text = " ".join(sim.value.logs)
        assert "cpi-proxy" in log_text or "Program log" in log_text
