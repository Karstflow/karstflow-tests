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
# Number of Write transactions broadcast before confirming a batch. Each tx
# reserves its full compute budget against the per-block cost limit (100M CU),
# so the batch must stay well under it (~32 * 1.4M = 45M) while still amortising
# the per-slot confirmation latency across many chunks.
BPF_LOADER_WRITE_BATCH = 32


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

    # Write program data in chunks. Broadcast writes in batches and confirm
    # each batch before starting the next. Confirming after every single chunk
    # costs ~1 slot per chunk (a multi-KB program took ~1 minute); broadcasting
    # all chunks at once instead overruns the per-block cost limit (every tx
    # reserves its full compute budget against the block). Batching overlaps the
    # per-slot confirmation latency while keeping each block within budget.
    offset = 0
    while offset < space:
        batch_sigs: list[str] = []
        for _ in range(BPF_LOADER_WRITE_BATCH):
            if offset >= space:
                break
            chunk = program_bytes[offset : offset + BPF_LOADER_WRITE_CHUNK]
            write_ix = _build_bpf_loader_write_ix(program_keypair.pubkey(), offset, chunk)
            blockhash_resp = await client.get_latest_blockhash()
            blockhash = blockhash_resp.value.blockhash
            msg = Message.new_with_blockhash([write_ix], payer.pubkey(), blockhash)
            tx = Transaction.new_unsigned(msg)
            tx.sign([payer, program_keypair], blockhash)
            resp = await client.send_transaction(tx)
            batch_sigs.append(str(resp.value))
            offset += BPF_LOADER_WRITE_CHUNK

        for sig in batch_sigs:
            await wait_for_confirmation(rpc_url, sig)

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


# --- BPF Loader Upgradeable helpers ---

# Upgradeable loader instruction discriminants (bincode u32 LE)
_UPG_INIT_BUFFER = 0
_UPG_WRITE = 1
_UPG_DEPLOY = 2
_UPG_UPGRADE = 3
_UPG_SET_AUTHORITY = 4
_UPG_CLOSE = 5

# Buffer account header: 4 bytes state enum + 32 bytes optional authority
_BUFFER_HEADER_SIZE = 37

SYSVAR_RENT = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
SYSVAR_CLOCK = Pubkey.from_string("SysvarC1ock11111111111111111111111111111111")


def _build_upg_init_buffer_ix(buffer: Pubkey, authority: Pubkey) -> Instruction:
    """InitializeBuffer instruction for BPF Loader Upgradeable."""
    data = struct.pack("<I", _UPG_INIT_BUFFER)
    return Instruction(
        program_id=BPF_LOADER_UPGRADEABLE,
        data=data,
        accounts=[
            AccountMeta(pubkey=buffer, is_signer=False, is_writable=True),
            AccountMeta(pubkey=authority, is_signer=False, is_writable=False),
        ],
    )


def _build_upg_write_ix(
    buffer: Pubkey, authority: Pubkey, offset: int, chunk: bytes
) -> Instruction:
    """Write instruction for BPF Loader Upgradeable."""
    data = (
        struct.pack("<I", _UPG_WRITE)
        + struct.pack("<I", offset)
        + struct.pack("<I", len(chunk))
        + chunk
    )
    return Instruction(
        program_id=BPF_LOADER_UPGRADEABLE,
        data=data,
        accounts=[
            AccountMeta(pubkey=buffer, is_signer=False, is_writable=True),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
        ],
    )


def _build_upg_deploy_ix(
    payer: Pubkey,
    programdata: Pubkey,
    program: Pubkey,
    buffer: Pubkey,
    authority: Pubkey,
) -> Instruction:
    """DeployWithMaxDataLen instruction for BPF Loader Upgradeable."""
    # bincode: u32 disc + u64 max_data_len
    # max_data_len is usually 2x the program size for future upgrades
    data = struct.pack("<I", _UPG_DEPLOY)
    return Instruction(
        program_id=BPF_LOADER_UPGRADEABLE,
        data=data,
        accounts=[
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=programdata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=program, is_signer=False, is_writable=True),
            AccountMeta(pubkey=buffer, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSVAR_RENT, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSVAR_CLOCK, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
        ],
    )


def _build_upg_upgrade_ix(
    programdata: Pubkey,
    program: Pubkey,
    buffer: Pubkey,
    spill: Pubkey,
    authority: Pubkey,
) -> Instruction:
    """Upgrade instruction for BPF Loader Upgradeable."""
    data = struct.pack("<I", _UPG_UPGRADE)
    return Instruction(
        program_id=BPF_LOADER_UPGRADEABLE,
        data=data,
        accounts=[
            AccountMeta(pubkey=programdata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=program, is_signer=False, is_writable=True),
            AccountMeta(pubkey=buffer, is_signer=False, is_writable=True),
            AccountMeta(pubkey=spill, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSVAR_RENT, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSVAR_CLOCK, is_signer=False, is_writable=False),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
        ],
    )


def _build_upg_set_authority_ix(
    account: Pubkey,
    current_authority: Pubkey,
    new_authority: Pubkey | None,
) -> Instruction:
    """SetAuthority instruction for BPF Loader Upgradeable."""
    data = struct.pack("<I", _UPG_SET_AUTHORITY)
    accounts = [
        AccountMeta(pubkey=account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=current_authority, is_signer=True, is_writable=False),
    ]
    if new_authority is not None:
        accounts.append(AccountMeta(pubkey=new_authority, is_signer=False, is_writable=False))
    return Instruction(
        program_id=BPF_LOADER_UPGRADEABLE,
        data=data,
        accounts=accounts,
    )


def _build_upg_close_ix(
    account: Pubkey,
    recipient: Pubkey,
    authority: Pubkey,
) -> Instruction:
    """Close instruction for BPF Loader Upgradeable."""
    data = struct.pack("<I", _UPG_CLOSE)
    return Instruction(
        program_id=BPF_LOADER_UPGRADEABLE,
        data=data,
        accounts=[
            AccountMeta(pubkey=account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=recipient, is_signer=False, is_writable=True),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
        ],
    )


def get_programdata_address(program_id: Pubkey) -> Pubkey:
    """Derive the programdata address for an upgradeable program."""
    seeds = [bytes(program_id)]
    pda, _bump = Pubkey.find_program_address(seeds, BPF_LOADER_UPGRADEABLE)
    return pda


async def _write_buffer(
    client: AsyncClient,
    payer: Keypair,
    buffer_kp: Keypair,
    authority: Keypair,
    program_bytes: bytes,
) -> None:
    """Create, initialize, and write program bytes to a buffer account."""
    rpc_url = await get_rpc_url(client)
    buffer_size = _BUFFER_HEADER_SIZE + len(program_bytes)

    # Create buffer account
    rent_resp = await client.get_minimum_balance_for_rent_exemption(buffer_size)
    lamports = rent_resp.value
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    create_ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=buffer_kp.pubkey(),
            lamports=lamports,
            space=buffer_size,
            owner=BPF_LOADER_UPGRADEABLE,
        )
    )
    init_ix = _build_upg_init_buffer_ix(buffer_kp.pubkey(), authority.pubkey())

    msg = Message.new_with_blockhash([create_ix, init_ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, buffer_kp], blockhash)
    resp = await client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    # Write bytecode in chunks
    offset = 0
    while offset < len(program_bytes):
        chunk = program_bytes[offset : offset + BPF_LOADER_WRITE_CHUNK]
        write_ix = _build_upg_write_ix(buffer_kp.pubkey(), authority.pubkey(), offset, chunk)
        blockhash_resp = await client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash([write_ix], payer.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([payer, authority], blockhash)
        resp = await client.send_transaction(tx)
        await wait_for_confirmation(rpc_url, str(resp.value))
        offset += BPF_LOADER_WRITE_CHUNK


async def deploy_program_upgradeable(
    client: AsyncClient,
    payer: Keypair,
    program_name: str,
    *,
    authority: Keypair | None = None,
    program_keypair: Keypair | None = None,
) -> tuple[Pubkey, Keypair]:
    """Deploy a program via BPF Loader Upgradeable.

    Returns (program_pubkey, authority_keypair).
    """
    program_bytes = load_program_bytes(program_name)
    if program_keypair is None:
        program_keypair = Keypair()
    if authority is None:
        authority = payer

    rpc_url = await get_rpc_url(client)

    # Write program to buffer
    buffer_kp = Keypair()
    await _write_buffer(client, payer, buffer_kp, authority, program_bytes)

    # Create program account (minimal, owned by upgradeable loader)
    program_len = 36  # UpgradeableLoaderState::Program size
    rent_resp = await client.get_minimum_balance_for_rent_exemption(program_len)
    lamports = rent_resp.value
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    create_ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=program_keypair.pubkey(),
            lamports=lamports,
            space=program_len,
            owner=BPF_LOADER_UPGRADEABLE,
        )
    )

    programdata = get_programdata_address(program_keypair.pubkey())

    deploy_ix = _build_upg_deploy_ix(
        payer.pubkey(),
        programdata,
        program_keypair.pubkey(),
        buffer_kp.pubkey(),
        authority.pubkey(),
    )

    msg = Message.new_with_blockhash([create_ix, deploy_ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, program_keypair, authority], blockhash)
    resp = await client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    return program_keypair.pubkey(), authority


async def upgrade_program(
    client: AsyncClient,
    payer: Keypair,
    program_id: Pubkey,
    new_program_name: str,
    authority: Keypair,
) -> None:
    """Upgrade an existing upgradeable program with new bytecode."""
    program_bytes = load_program_bytes(new_program_name)
    rpc_url = await get_rpc_url(client)

    # Write new program to a fresh buffer
    buffer_kp = Keypair()
    await _write_buffer(client, payer, buffer_kp, authority, program_bytes)

    programdata = get_programdata_address(program_id)

    upgrade_ix = _build_upg_upgrade_ix(
        programdata,
        program_id,
        buffer_kp.pubkey(),
        payer.pubkey(),
        authority.pubkey(),
    )

    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([upgrade_ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, authority], blockhash)
    resp = await client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))
