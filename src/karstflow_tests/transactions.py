"""Transaction builder utilities."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction


async def build_and_send_transfer(
    client: AsyncClient,
    sender: Keypair,
    recipient: Pubkey,
    lamports: int,
) -> str:
    """Build, sign, and send a SOL transfer. Returns signature string."""
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

    resp = await client.send_transaction(tx)
    return str(resp.value)
