"""Transaction builder utilities."""

from __future__ import annotations

import base64

from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from karstflow_tests.rpc import RpcClient


async def build_transfer(
    rpc: RpcClient,
    sender: Keypair,
    recipient: Pubkey,
    lamports: int,
) -> str:
    """Build and sign a SOL transfer transaction. Returns base64-encoded tx."""
    blockhash_resp = await rpc.request("getLatestBlockhash")
    blockhash = Hash.from_string(blockhash_resp["value"]["blockhash"])

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

    return base64.b64encode(bytes(tx)).decode("ascii")
