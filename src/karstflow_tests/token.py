"""SPL Token program helpers for testing token lifecycle.

Provides utilities for creating mints, token accounts, minting,
transferring, and burning tokens using raw instructions.
"""

from __future__ import annotations

import struct

from solana.rpc.async_api import AsyncClient
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import CreateAccountParams, create_account
from solders.transaction import Transaction

from karstflow_tests.programs import get_rpc_url
from karstflow_tests.wait import wait_for_confirmation

TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
SYSVAR_RENT = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

# Token instruction indices
INITIALIZE_MINT = 0
INITIALIZE_ACCOUNT = 1
TRANSFER = 3
MINT_TO = 7
BURN = 8
CLOSE_ACCOUNT = 9

# Token account sizes
MINT_SIZE = 82
TOKEN_ACCOUNT_SIZE = 165


def _build_initialize_mint_ix(
    mint: Pubkey,
    decimals: int,
    mint_authority: Pubkey,
    freeze_authority: Pubkey | None = None,
) -> Instruction:
    """Build InitializeMint instruction."""
    data = struct.pack("<BB", INITIALIZE_MINT, decimals)
    data += bytes(mint_authority)
    # COption<Pubkey> for freeze authority
    if freeze_authority:
        data += struct.pack("<I", 1) + bytes(freeze_authority)
    else:
        data += struct.pack("<I", 0)

    return Instruction(
        program_id=TOKEN_PROGRAM_ID,
        data=data,
        accounts=[
            AccountMeta(pubkey=mint, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSVAR_RENT, is_signer=False, is_writable=False),
        ],
    )


def _build_initialize_account_ix(
    account: Pubkey,
    mint: Pubkey,
    owner: Pubkey,
) -> Instruction:
    """Build InitializeAccount instruction."""
    data = struct.pack("<B", INITIALIZE_ACCOUNT)
    return Instruction(
        program_id=TOKEN_PROGRAM_ID,
        data=data,
        accounts=[
            AccountMeta(pubkey=account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=owner, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSVAR_RENT, is_signer=False, is_writable=False),
        ],
    )


def _build_mint_to_ix(
    mint: Pubkey,
    destination: Pubkey,
    authority: Pubkey,
    amount: int,
) -> Instruction:
    """Build MintTo instruction."""
    data = struct.pack("<BQ", MINT_TO, amount)
    return Instruction(
        program_id=TOKEN_PROGRAM_ID,
        data=data,
        accounts=[
            AccountMeta(pubkey=mint, is_signer=False, is_writable=True),
            AccountMeta(pubkey=destination, is_signer=False, is_writable=True),
            AccountMeta(pubkey=authority, is_signer=True, is_writable=False),
        ],
    )


def _build_token_transfer_ix(
    source: Pubkey,
    destination: Pubkey,
    owner: Pubkey,
    amount: int,
) -> Instruction:
    """Build Transfer instruction."""
    data = struct.pack("<BQ", TRANSFER, amount)
    return Instruction(
        program_id=TOKEN_PROGRAM_ID,
        data=data,
        accounts=[
            AccountMeta(pubkey=source, is_signer=False, is_writable=True),
            AccountMeta(pubkey=destination, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=True, is_writable=False),
        ],
    )


def _build_burn_ix(
    account: Pubkey,
    mint: Pubkey,
    owner: Pubkey,
    amount: int,
) -> Instruction:
    """Build Burn instruction."""
    data = struct.pack("<BQ", BURN, amount)
    return Instruction(
        program_id=TOKEN_PROGRAM_ID,
        data=data,
        accounts=[
            AccountMeta(pubkey=account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=True, is_writable=False),
        ],
    )


def _build_close_account_ix(
    account: Pubkey,
    destination: Pubkey,
    owner: Pubkey,
) -> Instruction:
    """Build CloseAccount instruction."""
    data = struct.pack("<B", CLOSE_ACCOUNT)
    return Instruction(
        program_id=TOKEN_PROGRAM_ID,
        data=data,
        accounts=[
            AccountMeta(pubkey=account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=destination, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=True, is_writable=False),
        ],
    )


async def create_mint(
    client: AsyncClient,
    payer: Keypair,
    *,
    decimals: int = 9,
    mint_authority: Pubkey | None = None,
    freeze_authority: Pubkey | None = None,
) -> Keypair:
    """Create a new SPL Token mint. Returns the mint keypair."""
    mint = Keypair()
    authority = mint_authority or payer.pubkey()
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    rent_resp = await client.get_minimum_balance_for_rent_exemption(MINT_SIZE)
    lamports = rent_resp.value

    create_ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=mint.pubkey(),
            lamports=lamports,
            space=MINT_SIZE,
            owner=TOKEN_PROGRAM_ID,
        )
    )
    init_ix = _build_initialize_mint_ix(mint.pubkey(), decimals, authority, freeze_authority)

    msg = Message.new_with_blockhash([create_ix, init_ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, mint], blockhash)

    resp = await client.send_transaction(tx)
    rpc_url = await get_rpc_url(client)
    await wait_for_confirmation(rpc_url, str(resp.value))
    return mint


async def create_token_account(
    client: AsyncClient,
    payer: Keypair,
    mint: Pubkey,
    owner: Pubkey,
) -> Keypair:
    """Create a new token account. Returns the account keypair."""
    account = Keypair()
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    rent_resp = await client.get_minimum_balance_for_rent_exemption(TOKEN_ACCOUNT_SIZE)
    lamports = rent_resp.value

    create_ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=account.pubkey(),
            lamports=lamports,
            space=TOKEN_ACCOUNT_SIZE,
            owner=TOKEN_PROGRAM_ID,
        )
    )
    init_ix = _build_initialize_account_ix(account.pubkey(), mint, owner)

    msg = Message.new_with_blockhash([create_ix, init_ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, account], blockhash)

    resp = await client.send_transaction(tx)
    rpc_url = await get_rpc_url(client)
    await wait_for_confirmation(rpc_url, str(resp.value))
    return account


async def mint_to(
    client: AsyncClient,
    payer: Keypair,
    mint: Pubkey,
    destination: Pubkey,
    authority: Keypair,
    amount: int,
) -> str:
    """Mint tokens to a destination account. Returns signature."""
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    ix = _build_mint_to_ix(mint, destination, authority.pubkey(), amount)
    signers = [payer]
    if authority.pubkey() != payer.pubkey():
        signers.append(authority)

    msg = Message.new_with_blockhash([ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign(signers, blockhash)

    resp = await client.send_transaction(tx)
    sig = str(resp.value)
    rpc_url = await get_rpc_url(client)
    await wait_for_confirmation(rpc_url, sig)
    return sig


async def token_transfer(
    client: AsyncClient,
    owner: Keypair,
    source: Pubkey,
    destination: Pubkey,
    amount: int,
) -> str:
    """Transfer tokens between accounts. Returns signature."""
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    ix = _build_token_transfer_ix(source, destination, owner.pubkey(), amount)
    msg = Message.new_with_blockhash([ix], owner.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([owner], blockhash)

    resp = await client.send_transaction(tx)
    sig = str(resp.value)
    rpc_url = await get_rpc_url(client)
    await wait_for_confirmation(rpc_url, sig)
    return sig


async def burn_tokens(
    client: AsyncClient,
    owner: Keypair,
    account: Pubkey,
    mint: Pubkey,
    amount: int,
) -> str:
    """Burn tokens from an account. Returns signature."""
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    ix = _build_burn_ix(account, mint, owner.pubkey(), amount)
    msg = Message.new_with_blockhash([ix], owner.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([owner], blockhash)

    resp = await client.send_transaction(tx)
    sig = str(resp.value)
    rpc_url = await get_rpc_url(client)
    await wait_for_confirmation(rpc_url, sig)
    return sig


async def close_token_account(
    client: AsyncClient,
    owner: Keypair,
    account: Pubkey,
    destination: Pubkey,
) -> str:
    """Close a token account, reclaiming rent. Returns signature."""
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    ix = _build_close_account_ix(account, destination, owner.pubkey())
    msg = Message.new_with_blockhash([ix], owner.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([owner], blockhash)

    resp = await client.send_transaction(tx)
    sig = str(resp.value)
    rpc_url = await get_rpc_url(client)
    await wait_for_confirmation(rpc_url, sig)
    return sig
