"""Tests for Program Derived Addresses (PDA) — derivation and account creation."""

from __future__ import annotations

import struct

import pytest
from solana.rpc.async_api import AsyncClient
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from karstflow_tests.programs import (
    SYSTEM_PROGRAM,
    deploy_program,
    get_rpc_url,
)
from karstflow_tests.wait import wait_for_confirmation

pytestmark = [pytest.mark.programs, pytest.mark.pda]


async def test_pda_derivation_deterministic() -> None:
    """Pubkey.find_program_address is deterministic — same seeds give same result."""
    program_id = Keypair().pubkey()
    seed = b"counter"
    pda1, bump1 = Pubkey.find_program_address([seed], program_id)
    pda2, bump2 = Pubkey.find_program_address([seed], program_id)
    assert pda1 == pda2
    assert bump1 == bump2


async def test_pda_different_seeds_different_addresses() -> None:
    """Different seeds produce different PDA addresses."""
    program_id = Keypair().pubkey()
    pda_a, _ = Pubkey.find_program_address([b"seed_a"], program_id)
    pda_b, _ = Pubkey.find_program_address([b"seed_b"], program_id)
    assert pda_a != pda_b


async def test_pda_different_programs_different_addresses() -> None:
    """Same seed + different program IDs produce different PDAs."""
    seed = b"shared_seed"
    prog_a = Keypair().pubkey()
    prog_b = Keypair().pubkey()
    pda_a, _ = Pubkey.find_program_address([seed], prog_a)
    pda_b, _ = Pubkey.find_program_address([seed], prog_b)
    assert pda_a != pda_b


async def test_pda_multiple_seeds() -> None:
    """PDA with multiple seeds works."""
    program_id = Keypair().pubkey()
    pda, bump = Pubkey.find_program_address(
        [b"prefix", b"suffix", bytes([42])], program_id
    )
    assert bump <= 255
    assert pda != program_id


async def test_pda_max_seeds() -> None:
    """PDA derivation with the maximum number of user seeds.

    Solana caps program-address derivation at MAX_SEEDS = 16, but
    ``find_program_address`` appends the bump as an extra seed, so the maximum
    number of *user* seeds is 15 (15 + bump = 16). Sixteen user seeds would push
    the total to 17 and exhaust every bump candidate.
    """
    program_id = Keypair().pubkey()
    seeds = [bytes([i]) for i in range(15)]
    _pda, bump = Pubkey.find_program_address(seeds, program_id)
    assert bump <= 255


async def test_pda_counter_initialize(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Deploy pda-counter, initialize PDA account, verify counter=0."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "pda_counter", program_keypair=program_kp
    )

    seed = b"test_counter"
    pda, _bump = Pubkey.find_program_address([seed], program_id)

    # Initialize: instruction 0, seed_len, seed
    ix_data = struct.pack("<BB", 0, len(seed)) + seed
    ix = Instruction(
        program_id=program_id,
        data=ix_data,
        accounts=[
            AccountMeta(pubkey=funded_keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    rpc_url = await get_rpc_url(solana_client)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Verify PDA account exists and has counter=0
    info = await solana_client.get_account_info(pda)
    assert info.value is not None
    assert str(info.value.owner) == str(program_id)
    counter = struct.unpack("<Q", bytes(info.value.data))[0]
    assert counter == 0


async def test_pda_counter_increment(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Initialize PDA counter, increment twice, verify counter=2."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "pda_counter", program_keypair=program_kp
    )

    seed = b"inc_test"
    pda, _bump = Pubkey.find_program_address([seed], program_id)
    rpc_url = await get_rpc_url(solana_client)

    # Initialize
    init_data = struct.pack("<BB", 0, len(seed)) + seed
    init_ix = Instruction(
        program_id=program_id,
        data=init_data,
        accounts=[
            AccountMeta(pubkey=funded_keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([init_ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Increment twice
    for _ in range(2):
        inc_ix = Instruction(
            program_id=program_id,
            data=bytes([1]),
            accounts=[
                AccountMeta(pubkey=pda, is_signer=False, is_writable=True),
            ],
        )
        blockhash_resp = await solana_client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([inc_ix], funded_keypair.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([funded_keypair], blockhash)
        resp = await solana_client.send_transaction(tx)
        await wait_for_confirmation(rpc_url, str(resp.value))

    # Read counter
    info = await solana_client.get_account_info(pda)
    assert info.value is not None
    counter = struct.unpack("<Q", bytes(info.value.data))[0]
    assert counter == 2


async def test_pda_account_owned_by_program(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """PDA account created by program is owned by that program."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "pda_counter", program_keypair=program_kp
    )

    seed = b"ownership"
    pda, _bump = Pubkey.find_program_address([seed], program_id)

    ix_data = struct.pack("<BB", 0, len(seed)) + seed
    ix = Instruction(
        program_id=program_id,
        data=ix_data,
        accounts=[
            AccountMeta(pubkey=funded_keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        ],
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    rpc_url = await get_rpc_url(solana_client)
    await wait_for_confirmation(rpc_url, str(resp.value))

    info = await solana_client.get_account_info(pda)
    assert info.value is not None
    assert str(info.value.owner) == str(program_id)
    assert not info.value.executable
