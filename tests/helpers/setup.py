"""Reusable account setup and transaction helpers for tests.

Centralizes common patterns to avoid duplication across test modules:
- funded_sender: create and fund a keypair with configurable amount
- transfer_pair: create funded sender + unfunded recipient
- send_simple_transfer: build and send a basic SOL transfer
- build_raw_transfer: build a signed Transaction object for lower-level tests
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from karstflow_tests.wait import wait_for_confirmation


async def funded_sender(
    client: AsyncClient,
    rpc_url: str,
    lamports: int = 5_000_000_000,
) -> Keypair:
    """Create a funded keypair ready to send transactions."""
    kp = Keypair()
    resp = await client.request_airdrop(kp.pubkey(), lamports)
    await wait_for_confirmation(rpc_url, str(resp.value))
    return kp


async def transfer_pair(
    client: AsyncClient,
    rpc_url: str,
    sender_lamports: int = 5_000_000_000,
) -> tuple[Keypair, Keypair]:
    """Create a funded sender and unfunded recipient pair."""
    sender = await funded_sender(client, rpc_url, sender_lamports)
    recipient = Keypair()
    return sender, recipient


async def send_simple_transfer(
    client: AsyncClient,
    rpc_url: str,
    sender: Keypair,
    recipient: Pubkey,
    lamports: int,
) -> str:
    """Build, sign, send, and confirm a SOL transfer. Returns signature."""
    tx = await build_raw_transfer(client, sender, recipient, lamports)
    resp = await client.send_transaction(tx)
    sig = str(resp.value)
    await wait_for_confirmation(rpc_url, sig)
    return sig


async def build_raw_transfer(
    client: AsyncClient,
    sender: Keypair,
    recipient: Pubkey,
    lamports: int,
) -> Transaction:
    """Build and sign a SOL transfer transaction (does not send)."""
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=recipient,
            lamports=lamports,
        )
    )
    msg = Message.new_with_blockhash([ix], sender.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([sender], blockhash)
    return tx


async def airdrop_and_confirm(
    client: AsyncClient,
    rpc_url: str,
    pubkey: Pubkey,
    lamports: int = 1_000_000_000,
) -> str:
    """Airdrop to pubkey and wait for confirmation. Returns signature."""
    resp = await client.request_airdrop(pubkey, lamports)
    sig = str(resp.value)
    await wait_for_confirmation(rpc_url, sig)
    return sig
