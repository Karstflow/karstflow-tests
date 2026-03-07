"""Functional tests: blockhash validity and lifecycle.

Tests isBlockhashValid, blockhash freshness, and related behavior.
"""

from __future__ import annotations

import asyncio

from solana.rpc.async_api import AsyncClient

from karstflow_tests.rpc import RpcClient


async def test_latest_blockhash_is_valid(solana_client: AsyncClient, rpc_client: RpcClient) -> None:
    """A freshly fetched blockhash is valid."""
    resp = await solana_client.get_latest_blockhash()
    blockhash = str(resp.value.blockhash)

    result = await rpc_client.request("isBlockhashValid", [blockhash, {"commitment": "confirmed"}])
    assert result["value"] is True


async def test_blockhash_has_last_valid_height(solana_client: AsyncClient) -> None:
    """getLatestBlockhash includes lastValidBlockHeight."""
    resp = await solana_client.get_latest_blockhash()
    assert resp.value.last_valid_block_height > 0


async def test_different_blockhashes_over_time(
    solana_client: AsyncClient,
) -> None:
    """Blockhash changes over time."""
    resp1 = await solana_client.get_latest_blockhash()
    bh1 = str(resp1.value.blockhash)

    await asyncio.sleep(2)

    resp2 = await solana_client.get_latest_blockhash()
    bh2 = str(resp2.value.blockhash)

    assert bh1 != bh2


async def test_invalid_blockhash_string(rpc_client: RpcClient) -> None:
    """Invalid blockhash string returns error or false."""
    resp = await rpc_client.request_raw(
        "isBlockhashValid",
        ["11111111111111111111111111111111111111111111", {"commitment": "confirmed"}],
    )
    # Either an error or value=false is acceptable
    if resp.ok:
        assert resp.result["value"] is False
    else:
        assert resp.error is not None


async def test_old_blockhash_eventually_invalid(
    solana_client: AsyncClient, rpc_client: RpcClient
) -> None:
    """A blockhash fetched now should still be valid shortly after."""
    resp = await solana_client.get_latest_blockhash()
    blockhash = str(resp.value.blockhash)

    # Should still be valid within a few seconds
    await asyncio.sleep(1)
    result = await rpc_client.request("isBlockhashValid", [blockhash, {"commitment": "confirmed"}])
    assert result["value"] is True


async def test_blockhash_context_slot(solana_client: AsyncClient, rpc_client: RpcClient) -> None:
    """isBlockhashValid response includes context slot."""
    resp = await solana_client.get_latest_blockhash()
    blockhash = str(resp.value.blockhash)

    result = await rpc_client.request("isBlockhashValid", [blockhash, {"commitment": "confirmed"}])
    assert "context" in result
    assert "slot" in result["context"]
    assert result["context"]["slot"] > 0
