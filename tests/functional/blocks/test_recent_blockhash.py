"""Functional tests: getLatestBlockhash, isBlockhashValid, getFeeForMessage."""

from __future__ import annotations

import asyncio

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.message import Message
from solders.system_program import TransferParams, transfer

from karstflow_tests.rpc import RpcClient


async def test_latest_blockhash_format(solana_client: AsyncClient) -> None:
    """getLatestBlockhash returns blockhash and lastValidBlockHeight."""
    result = await solana_client.get_latest_blockhash()
    blockhash = result.value.blockhash
    last_valid = result.value.last_valid_block_height
    assert str(blockhash)
    assert len(str(blockhash)) > 30
    assert isinstance(last_valid, int)
    assert last_valid > 0


async def test_latest_blockhash_changes(solana_client: AsyncClient) -> None:
    """Blockhash changes as slots advance."""
    h1 = str((await solana_client.get_latest_blockhash()).value.blockhash)
    await asyncio.sleep(1)
    h2 = str((await solana_client.get_latest_blockhash()).value.blockhash)
    assert h1 != h2


async def test_blockhash_valid(rpc_client: RpcClient) -> None:
    """Recently fetched blockhash is valid."""
    bh_result = await rpc_client.request("getLatestBlockhash")
    blockhash = bh_result["value"]["blockhash"]
    valid = await rpc_client.request("isBlockhashValid", [blockhash])
    assert valid["value"] is True


async def test_fee_for_message(solana_client: AsyncClient, rpc_client: RpcClient) -> None:
    """getFeeForMessage returns fee for a serialized message."""
    kp = Keypair()
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    ix = transfer(
        TransferParams(
            from_pubkey=kp.pubkey(),
            to_pubkey=Keypair().pubkey(),
            lamports=1_000_000,
        )
    )
    msg = Message.new_with_blockhash([ix], kp.pubkey(), blockhash)

    # Serialize message to base64 for getFeeForMessage
    import base64

    msg_bytes = bytes(msg)
    msg_b64 = base64.b64encode(msg_bytes).decode()

    result = await rpc_client.request("getFeeForMessage", [msg_b64])
    assert isinstance(result, dict)
    assert "value" in result
    if result["value"] is not None:
        assert isinstance(result["value"], int)
        assert result["value"] > 0  # fee should be positive
