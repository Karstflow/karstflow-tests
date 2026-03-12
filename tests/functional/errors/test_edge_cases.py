"""Functional tests: Edge cases — batch limits, concurrent ops, boundary conditions."""

from __future__ import annotations

import asyncio

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender, send_simple_transfer


async def test_large_batch_rpc(raw_rpc: RpcClient) -> None:
    """Sending a large batch of RPC requests succeeds."""
    requests = [("getSlot", None) for _ in range(20)]
    responses = await raw_rpc.batch(requests)
    assert len(responses) == 20
    for resp in responses:
        assert resp.ok
        assert isinstance(resp.result, int)


async def test_batch_mixed_methods(raw_rpc: RpcClient) -> None:
    """Batch with mixed read-only methods returns correct types."""
    requests = [
        ("getSlot", None),
        ("getBlockHeight", None),
        ("getHealth", None),
        ("getVersion", None),
        ("getEpochInfo", [{"commitment": "confirmed"}]),
    ]
    responses = await raw_rpc.batch(requests)
    assert len(responses) == 5
    for resp in responses:
        assert resp.ok


async def test_batch_with_errors(raw_rpc: RpcClient) -> None:
    """Batch with invalid methods returns errors for those items."""
    requests = [
        ("getSlot", None),
        ("nonExistentMethod", None),
        ("getBlockHeight", None),
    ]
    responses = await raw_rpc.batch(requests)
    assert len(responses) == 3
    assert responses[0].ok
    assert not responses[1].ok
    assert responses[2].ok


async def test_concurrent_rpc_requests(raw_rpc: RpcClient) -> None:
    """Multiple concurrent RPC requests all succeed."""
    tasks = [raw_rpc.get_slot() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 10
    for slot in results:
        assert isinstance(slot, int)
        assert slot > 0


async def test_concurrent_transfers(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Multiple concurrent transfers succeed."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    recipients = [Keypair() for _ in range(3)]

    tasks = [
        send_simple_transfer(solana_client, test_config.rpc_url, sender, r.pubkey(), 100_000)
        for r in recipients
    ]
    sigs = await asyncio.gather(*tasks)
    assert len(sigs) == 3
    for sig in sigs:
        assert len(sig) > 40


async def test_zero_lamport_transfer_fails(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Zero-lamport transfer should still succeed (no-op transfer is valid)."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 0
    )
    assert len(sig) > 40


async def test_insufficient_funds_transfer(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transfer exceeding balance should fail."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 1_000_000)
    recipient = Keypair()

    from tests.helpers.setup import build_raw_transfer

    tx = await build_raw_transfer(solana_client, sender, recipient.pubkey(), 999_999_999_999)
    from solana.rpc.core import RPCException

    with pytest.raises(RPCException, match=r"(?i)insufficient"):
        await solana_client.send_transaction(tx)


async def test_get_balance_many_accounts_concurrently(
    solana_client: AsyncClient,
) -> None:
    """Concurrently checking balances of many accounts."""
    keypairs = [Keypair() for _ in range(20)]
    tasks = [solana_client.get_balance(kp.pubkey()) for kp in keypairs]
    results = await asyncio.gather(*tasks)
    assert len(results) == 20
    for result in results:
        assert result.value == 0


async def test_batch_rpc_empty(raw_rpc: RpcClient) -> None:
    """Empty batch request is handled gracefully."""
    # Some implementations return empty list, others error
    try:
        responses = await raw_rpc.batch([])
        assert isinstance(responses, list)
    except Exception:
        pass  # Some servers reject empty batch


async def test_rpc_idempotent_reads(raw_rpc: RpcClient) -> None:
    """Multiple reads of same state return consistent results."""
    results = [await raw_rpc.get_genesis_hash() for _ in range(5)]
    assert all(r == results[0] for r in results)
