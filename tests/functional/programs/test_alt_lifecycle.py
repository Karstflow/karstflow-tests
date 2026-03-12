"""Tests for Address Lookup Table (ALT) lifecycle operations."""

from __future__ import annotations

import struct

import pytest
from solana.rpc.async_api import AsyncClient
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from karstflow_tests.programs import SYSTEM_PROGRAM, get_rpc_url
from karstflow_tests.wait import wait_for_confirmation

ALT_PROGRAM = Pubkey.from_string("AddressLookupTab1e1111111111111111111111111")

pytestmark = [pytest.mark.programs, pytest.mark.alt]


def _derive_alt_address(
    authority: Pubkey, recent_slot: int
) -> tuple[Pubkey, int]:
    """Derive ALT address from authority and recent slot."""
    slot_bytes = struct.pack("<Q", recent_slot)
    return Pubkey.find_program_address(
        [bytes(authority), slot_bytes], ALT_PROGRAM
    )


def _build_create_alt_ix(
    payer: Pubkey,
    authority: Pubkey,
    recent_slot: int,
    alt_address: Pubkey,
) -> Instruction:
    """Build CreateLookupTable instruction."""
    # Instruction 0: CreateLookupTable
    # Data: u32(0) + u64(recent_slot) + u8(bump)
    _, bump = _derive_alt_address(authority, recent_slot)
    data = struct.pack("<IQB", 0, recent_slot, bump)
    return Instruction(
        program_id=ALT_PROGRAM,
        data=data,
        accounts=[
            AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )


def _build_extend_alt_ix(
    alt_address: Pubkey,
    authority: Pubkey,
    payer: Pubkey,
    addresses: list[Pubkey],
) -> Instruction:
    """Build ExtendLookupTable instruction."""
    # Instruction 2: ExtendLookupTable
    # Data: u32(2) + u64(count) + [Pubkey; count]
    data = struct.pack("<IQ", 2, len(addresses))
    for addr in addresses:
        data += bytes(addr)
    return Instruction(
        program_id=ALT_PROGRAM,
        data=data,
        accounts=[
            AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )


def _build_deactivate_alt_ix(
    alt_address: Pubkey, authority: Pubkey
) -> Instruction:
    """Build DeactivateLookupTable instruction."""
    data = struct.pack("<I", 3)
    return Instruction(
        program_id=ALT_PROGRAM,
        data=data,
        accounts=[
            AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
        ],
    )


def _build_close_alt_ix(
    alt_address: Pubkey, authority: Pubkey, recipient: Pubkey
) -> Instruction:
    """Build CloseLookupTable instruction."""
    data = struct.pack("<I", 4)
    return Instruction(
        program_id=ALT_PROGRAM,
        data=data,
        accounts=[
            AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
            AccountMeta(pubkey=recipient, is_signer=False, is_writable=True),
        ],
    )


async def _get_recent_slot(client: AsyncClient) -> int:
    """Get a recent slot for ALT creation."""
    slot_resp = await client.get_slot()
    return slot_resp.value


async def test_create_lookup_table(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Create an Address Lookup Table and verify it exists."""
    recent_slot = await _get_recent_slot(solana_client)
    alt_address, _ = _derive_alt_address(funded_keypair.pubkey(), recent_slot)

    ix = _build_create_alt_ix(
        funded_keypair.pubkey(),
        funded_keypair.pubkey(),
        recent_slot,
        alt_address,
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    rpc_url = await get_rpc_url(solana_client)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Verify ALT account exists
    info = await solana_client.get_account_info(alt_address)
    assert info.value is not None
    assert str(info.value.owner) == str(ALT_PROGRAM)


async def test_extend_lookup_table(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Create ALT, extend with addresses, verify account data grew."""
    recent_slot = await _get_recent_slot(solana_client)
    alt_address, _ = _derive_alt_address(funded_keypair.pubkey(), recent_slot)
    rpc_url = await get_rpc_url(solana_client)

    # Create
    create_ix = _build_create_alt_ix(
        funded_keypair.pubkey(),
        funded_keypair.pubkey(),
        recent_slot,
        alt_address,
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([create_ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Get size before extend
    info_before = await solana_client.get_account_info(alt_address)
    size_before = len(info_before.value.data) if info_before.value else 0

    # Extend with 3 addresses
    extra_addrs = [Keypair().pubkey() for _ in range(3)]
    extend_ix = _build_extend_alt_ix(
        alt_address, funded_keypair.pubkey(), funded_keypair.pubkey(), extra_addrs
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([extend_ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Verify data grew by 3 * 32 bytes
    info_after = await solana_client.get_account_info(alt_address)
    assert info_after.value is not None
    size_after = len(info_after.value.data)
    assert size_after == size_before + 3 * 32


async def test_deactivate_lookup_table(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Create ALT, deactivate it — should succeed."""
    recent_slot = await _get_recent_slot(solana_client)
    alt_address, _ = _derive_alt_address(funded_keypair.pubkey(), recent_slot)
    rpc_url = await get_rpc_url(solana_client)

    # Create
    create_ix = _build_create_alt_ix(
        funded_keypair.pubkey(),
        funded_keypair.pubkey(),
        recent_slot,
        alt_address,
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([create_ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Deactivate
    deactivate_ix = _build_deactivate_alt_ix(alt_address, funded_keypair.pubkey())
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([deactivate_ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Account should still exist (deactivated, not closed)
    info = await solana_client.get_account_info(alt_address)
    assert info.value is not None


async def test_alt_wrong_authority_fails(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Deactivate ALT with wrong authority should fail."""
    recent_slot = await _get_recent_slot(solana_client)
    alt_address, _ = _derive_alt_address(funded_keypair.pubkey(), recent_slot)
    rpc_url = await get_rpc_url(solana_client)

    # Create with funded_keypair as authority
    create_ix = _build_create_alt_ix(
        funded_keypair.pubkey(),
        funded_keypair.pubkey(),
        recent_slot,
        alt_address,
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([create_ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Try deactivate with a different keypair
    wrong_authority = Keypair()
    airdrop_resp = await solana_client.request_airdrop(wrong_authority.pubkey(), 1_000_000_000)
    await wait_for_confirmation(rpc_url, str(airdrop_resp.value))

    deactivate_ix = _build_deactivate_alt_ix(alt_address, wrong_authority.pubkey())
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([deactivate_ix], wrong_authority.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([wrong_authority], blockhash)

    sim = await solana_client.simulate_transaction(tx)
    assert sim.value.err is not None
