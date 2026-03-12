"""Program deployment and execution helpers for integration tests.

Provides utilities for deploying BPF programs, creating program accounts,
and building program instructions for testing the validator's SBPF runtime.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from solana.rpc.async_api import AsyncClient
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import (
    CreateAccountParams,
    create_account,
)
from solders.transaction import Transaction

from karstflow_tests.wait import wait_for_confirmation

BPF_LOADER = Pubkey.from_string("BPFLoader2111111111111111111111111111111111")
BPF_LOADER_UPGRADEABLE = Pubkey.from_string("BPFLoaderUpgradeab1e11111111111111111111111")
MEMO_PROGRAM_V2 = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "programs"

# BPF Loader v2 write chunk size (must fit in single tx)
BPF_LOADER_WRITE_CHUNK = 900


async def get_rpc_url(client: AsyncClient) -> str:
    return str(client._provider.endpoint_uri)


def build_memo_instruction(
    memo_text: str,
    signer: Pubkey,
) -> Instruction:
    """Build a Memo program instruction."""
    return Instruction(
        program_id=MEMO_PROGRAM_V2,
        data=memo_text.encode("utf-8"),
        accounts=[AccountMeta(pubkey=signer, is_signer=True, is_writable=True)],
    )


async def send_memo(
    client: AsyncClient,
    signer: Keypair,
    memo_text: str,
    *,
    confirm: bool = True,
) -> str:
    """Send a memo transaction. Returns signature."""
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    ix = build_memo_instruction(memo_text, signer.pubkey())
    msg = Message.new_with_blockhash([ix], signer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([signer], blockhash)

    resp = await client.send_transaction(tx)
    sig = str(resp.value)
    if confirm:
        rpc_url = await get_rpc_url(client)
        await wait_for_confirmation(rpc_url, sig)
    return sig


def build_create_account_ix(
    payer: Pubkey,
    new_account: Pubkey,
    lamports: int,
    space: int,
    owner: Pubkey,
) -> Instruction:
    """Build a CreateAccount system instruction."""
    return create_account(
        CreateAccountParams(
            from_pubkey=payer,
            to_pubkey=new_account,
            lamports=lamports,
            space=space,
            owner=owner,
        )
    )


async def create_program_owned_account(
    client: AsyncClient,
    payer: Keypair,
    owner: Pubkey,
    space: int = 128,
) -> Keypair:
    """Create an account owned by a program. Returns the new account keypair."""
    new_account = Keypair()
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    rent_resp = await client.get_minimum_balance_for_rent_exemption(space)
    lamports = rent_resp.value

    ix = build_create_account_ix(payer.pubkey(), new_account.pubkey(), lamports, space, owner)
    msg = Message.new_with_blockhash([ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, new_account], blockhash)

    resp = await client.send_transaction(tx)
    rpc_url = await get_rpc_url(client)
    await wait_for_confirmation(rpc_url, str(resp.value))
    return new_account


def build_compute_budget_set_units(units: int) -> Instruction:
    """Build ComputeBudget SetComputeUnitLimit instruction."""
    # Program: ComputeBudget111111111111111111111111111111
    compute_budget = Pubkey.from_string("ComputeBudget111111111111111111111111111111")
    # Instruction 2: SetComputeUnitLimit (u8=2, u32=units)
    data = struct.pack("<BI", 2, units)
    return Instruction(program_id=compute_budget, data=data, accounts=[])


def build_compute_budget_set_price(micro_lamports: int) -> Instruction:
    """Build ComputeBudget SetComputeUnitPrice instruction."""
    compute_budget = Pubkey.from_string("ComputeBudget111111111111111111111111111111")
    # Instruction 3: SetComputeUnitPrice (u8=3, u64=price)
    data = struct.pack("<BQ", 3, micro_lamports)
    return Instruction(program_id=compute_budget, data=data, accounts=[])


async def build_multi_instruction_tx(
    client: AsyncClient,
    signer: Keypair,
    instructions: list[Instruction],
) -> Transaction:
    """Build a transaction with multiple instructions."""
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash(instructions, signer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([signer], blockhash)
    return tx


async def send_multi_instruction_tx(
    client: AsyncClient,
    signer: Keypair,
    instructions: list[Instruction],
    *,
    confirm: bool = True,
) -> str:
    """Build and send a transaction with multiple instructions. Returns signature."""
    tx = await build_multi_instruction_tx(client, signer, instructions)
    resp = await client.send_transaction(tx)
    sig = str(resp.value)
    if confirm:
        rpc_url = await get_rpc_url(client)
        await wait_for_confirmation(rpc_url, sig)
    return sig


async def create_nonce_account(
    client: AsyncClient,
    payer: Keypair,
    *,
    lamports: int | None = None,
) -> Keypair:
    """Create a nonce account for durable transactions. Returns nonce account keypair."""
    nonce_account = Keypair()
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    # Nonce account needs 80 bytes of space
    nonce_space = 80
    if lamports is None:
        rent_resp = await client.get_minimum_balance_for_rent_exemption(nonce_space)
        lamports = rent_resp.value

    # Create account owned by system program
    create_ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=nonce_account.pubkey(),
            lamports=lamports,
            space=nonce_space,
            owner=SYSTEM_PROGRAM,
        )
    )
    # Initialize nonce: system program instruction index 6
    # Layout: u32 instruction_type(6) + 32-byte authorized_pubkey
    init_data = struct.pack("<I", 6) + bytes(payer.pubkey())
    init_ix = Instruction(
        program_id=SYSTEM_PROGRAM,
        data=init_data,
        accounts=[
            AccountMeta(pubkey=nonce_account.pubkey(), is_signer=False, is_writable=True),
            AccountMeta(
                pubkey=Pubkey.from_string("SysvarRecentB1ockHashes11111111111111111111"),
                is_signer=False,
                is_writable=False,
            ),
            AccountMeta(
                pubkey=Pubkey.from_string("SysvarRent111111111111111111111111111111111"),
                is_signer=False,
                is_writable=False,
            ),
        ],
    )

    msg = Message.new_with_blockhash([create_ix, init_ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, nonce_account], blockhash)

    resp = await client.send_transaction(tx)
    rpc_url = await get_rpc_url(client)
    await wait_for_confirmation(rpc_url, str(resp.value))
    return nonce_account


def load_program_bytes(name: str) -> bytes:
    """Load compiled .so program bytes from fixtures directory."""
    so_path = FIXTURES_DIR / f"{name}.so"
    if not so_path.exists():
        msg = f"Program .so not found: {so_path}"
        raise FileNotFoundError(msg)
    return so_path.read_bytes()


def load_program_keypair(name: str) -> Keypair:
    """Load program keypair from fixtures directory."""
    kp_path = FIXTURES_DIR / f"{name}-keypair.json"
    if not kp_path.exists():
        msg = f"Program keypair not found: {kp_path}"
        raise FileNotFoundError(msg)
    secret_bytes = bytes(json.loads(kp_path.read_text()))
    return Keypair.from_bytes(secret_bytes)


def _build_bpf_loader_write_ix(
    program_account: Pubkey,
    offset: int,
    chunk: bytes,
) -> Instruction:
    """Build BPF Loader v2 Write instruction (bincode format)."""
    # bincode: disc(u32) + offset(u32) + vec_len(u64) + data
    data = struct.pack("<IIQ", 0, offset, len(chunk)) + chunk
    return Instruction(
        program_id=BPF_LOADER,
        data=data,
        accounts=[
            AccountMeta(pubkey=program_account, is_signer=True, is_writable=True),
        ],
    )


def _build_bpf_loader_finalize_ix(program_account: Pubkey) -> Instruction:
    """Build BPF Loader v2 Finalize instruction."""
    rent_sysvar = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
    data = struct.pack("<I", 1)
    return Instruction(
        program_id=BPF_LOADER,
        data=data,
        accounts=[
            AccountMeta(pubkey=program_account, is_signer=True, is_writable=True),
            AccountMeta(pubkey=rent_sysvar, is_signer=False, is_writable=False),
        ],
    )


async def deploy_program(
    client: AsyncClient,
    payer: Keypair,
    program_name: str,
    *,
    program_keypair: Keypair | None = None,
) -> Pubkey:
    """Deploy a BPF program via BPF Loader v2.

    Loads .so from fixtures, creates program account, writes bytecode
    in chunks, and finalizes. Returns the program pubkey.
    """
    program_bytes = load_program_bytes(program_name)
    if program_keypair is None:
        program_keypair = load_program_keypair(program_name)

    rpc_url = await get_rpc_url(client)
    space = len(program_bytes)

    # Create program account
    rent_resp = await client.get_minimum_balance_for_rent_exemption(space)
    lamports = rent_resp.value
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    create_ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=program_keypair.pubkey(),
            lamports=lamports,
            space=space,
            owner=BPF_LOADER,
        )
    )
    msg = Message.new_with_blockhash([create_ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, program_keypair], blockhash)
    resp = await client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Write program data in chunks
    offset = 0
    while offset < space:
        chunk = program_bytes[offset : offset + BPF_LOADER_WRITE_CHUNK]
        write_ix = _build_bpf_loader_write_ix(
            program_keypair.pubkey(), offset, chunk
        )
        blockhash_resp = await client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([write_ix], payer.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([payer, program_keypair], blockhash)
        resp = await client.send_transaction(tx)
        await wait_for_confirmation(rpc_url, str(resp.value))
        offset += BPF_LOADER_WRITE_CHUNK

    # Finalize
    finalize_ix = _build_bpf_loader_finalize_ix(program_keypair.pubkey())
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([finalize_ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, program_keypair], blockhash)
    resp = await client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    return program_keypair.pubkey()
