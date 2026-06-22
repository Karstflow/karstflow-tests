"""Functional tests: account-lock limit + versioned (v0) tx with Address Lookup Tables.

Validates that the node enforces MAX_TRANSACTION_ACCOUNT_LOCKS = 64 (the
upstream-reverted value, not the briefly-raised 128). Reaching >64 locks is only
possible with an Address Lookup Table — a legacy transaction cannot fit that many
account keys within the 1232-byte MTU — so these tests also exercise the v0 /
ALT resolution path end to end.
"""

from __future__ import annotations

import struct

import pytest
from solana.rpc.async_api import AsyncClient
from solders.address_lookup_table_account import AddressLookupTableAccount
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message, MessageV0
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction, VersionedTransaction

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import MEMO_PROGRAM_V2, SYSTEM_PROGRAM
from karstflow_tests.wait import wait_for_confirmation
from tests.helpers.setup import funded_sender

ALT_PROGRAM = Pubkey.from_string("AddressLookupTab1e1111111111111111111111111")
# Max ALT addresses per ExtendLookupTable tx that stays within the 1232-byte MTU.
_EXTEND_BATCH = 20


def _build_create_alt_ix(
    payer: Pubkey, authority: Pubkey, recent_slot: int, alt_address: Pubkey, bump: int
) -> Instruction:
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
    alt_address: Pubkey, authority: Pubkey, payer: Pubkey, addresses: list[Pubkey]
) -> Instruction:
    data = struct.pack("<IQ", 2, len(addresses)) + b"".join(bytes(a) for a in addresses)
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


async def _send_legacy(client: AsyncClient, rpc_url: str, payer: Keypair, ix: Instruction) -> None:
    blockhash = (await client.get_latest_blockhash()).value.blockhash
    tx = Transaction.new_unsigned(Message.new_with_blockhash([ix], payer.pubkey(), blockhash))
    tx.sign([payer], blockhash)
    resp = await client.send_transaction(tx)
    await wait_for_confirmation(rpc_url, str(resp.value))


async def _create_alt_with_addresses(
    client: AsyncClient, rpc_url: str, payer: Keypair, addresses: list[Pubkey]
) -> Pubkey:
    """Create an ALT owned by ``payer`` and extend it with ``addresses``."""
    recent_slot = (await client.get_slot()).value
    slot_bytes = struct.pack("<Q", recent_slot)
    alt_address, bump = Pubkey.find_program_address(
        [bytes(payer.pubkey()), slot_bytes], ALT_PROGRAM
    )
    await _send_legacy(
        client,
        rpc_url,
        payer,
        _build_create_alt_ix(payer.pubkey(), payer.pubkey(), recent_slot, alt_address, bump),
    )
    for i in range(0, len(addresses), _EXTEND_BATCH):
        batch = addresses[i : i + _EXTEND_BATCH]
        await _send_legacy(
            client,
            rpc_url,
            payer,
            _build_extend_alt_ix(alt_address, payer.pubkey(), payer.pubkey(), batch),
        )
    return alt_address


@pytest.mark.xfail(
    reason="node gap: v0/ALT loaded-address resolution incomplete — the execute "
    "path (dev-mode RPC) does not resolve address_table_lookups and the simulate "
    "path's resolution is ineffective; see QB-019. Flips to xpass when fixed.",
    strict=False,
)
async def test_alt_v0_transfer_executes(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """A versioned (v0) transfer resolved through an ALT executes successfully.

    Establishes that ALT resolution works end to end, so a rejection in the
    over-limit test below can only be the account-lock cap, not an ALT failure.
    """
    rpc_url = test_config.rpc_url
    payer = await funded_sender(solana_client, rpc_url, 10_000_000_000)
    recipient = Keypair()
    alt = await _create_alt_with_addresses(solana_client, rpc_url, payer, [recipient.pubkey()])
    # ALT becomes usable in a slot after the one it was extended in.
    await wait_for_confirmation(
        rpc_url, str((await solana_client.request_airdrop(payer.pubkey(), 1)).value)
    )

    alt_acc = AddressLookupTableAccount(key=alt, addresses=[recipient.pubkey()])
    ix = transfer(
        TransferParams(from_pubkey=payer.pubkey(), to_pubkey=recipient.pubkey(), lamports=250_000)
    )
    blockhash = (await solana_client.get_latest_blockhash()).value.blockhash
    msg = MessageV0.try_compile(payer.pubkey(), [ix], [alt_acc], blockhash)
    vtx = VersionedTransaction(msg, [payer])
    resp = await solana_client.send_transaction(vtx)
    await wait_for_confirmation(rpc_url, str(resp.value))

    assert (await solana_client.get_balance(recipient.pubkey())).value == 250_000


@pytest.mark.xfail(
    reason="depends on v0/ALT loaded-address resolution (node gap, QB-019): the ALT "
    "setup or v0 resolution currently fails before the 64-lock limit can be exercised. "
    "Flips to xpass when v0+ALT support lands.",
    strict=False,
)
async def test_account_locks_over_limit_rejected(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """A v0 transaction resolving >64 account locks via an ALT is rejected.

    70 locks is below the old 128 limit, so acceptance here would mean the limit
    regressed; the ALT keeps the wire tx small, so rejection is the lock cap (64)
    and not the 1232-byte MTU.
    """
    rpc_url = test_config.rpc_url
    payer = await funded_sender(solana_client, rpc_url, 10_000_000_000)
    addresses = [Keypair().pubkey() for _ in range(70)]
    alt = await _create_alt_with_addresses(solana_client, rpc_url, payer, addresses)
    await wait_for_confirmation(
        rpc_url, str((await solana_client.request_airdrop(payer.pubkey(), 1)).value)
    )

    alt_acc = AddressLookupTableAccount(key=alt, addresses=addresses)
    # Reference all 70 addresses (read-only) in a memo ix; sanitize-time lock
    # counting (payer + 70 = 71 > 64) rejects before the memo program runs.
    ix = Instruction(
        program_id=MEMO_PROGRAM_V2,
        data=b"",
        accounts=[AccountMeta(pubkey=a, is_signer=False, is_writable=False) for a in addresses],
    )
    blockhash = (await solana_client.get_latest_blockhash()).value.blockhash
    msg = MessageV0.try_compile(payer.pubkey(), [ix], [alt_acc], blockhash)
    vtx = VersionedTransaction(msg, [payer])

    rejected = False
    detail = "accepted"
    try:
        resp = await solana_client.send_transaction(vtx)
    except Exception as exc:  # node rejects at preflight (too many locks)
        rejected = True
        detail = f"send rejected: {type(exc).__name__}: {str(exc)[:120]}"
    else:
        status = await solana_client.get_signature_statuses([resp.value])
        value = status.value[0]
        rejected = value is None or value.err is not None
        detail = "dropped" if value is None else f"err={getattr(value, 'err', None)}"

    assert rejected, f"71-lock v0 tx must be rejected (limit 64, not 128); got: {detail}"
