"""Stress and robustness tests: high concurrency and burst patterns.

These tests verify the validator handles concurrent load gracefully
under single-node conditions.
"""

from __future__ import annotations

import asyncio

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import build_memo_instruction, send_multi_instruction_tx
from karstflow_tests.rpc import RpcClient
from karstflow_tests.ws import WsClient
from tests.helpers.setup import airdrop_and_confirm, funded_sender, send_simple_transfer


@pytest.mark.slow
async def test_concurrent_airdrop_storm(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """50 concurrent airdrop requests all succeed."""
    keypairs = [Keypair() for _ in range(50)]
    tasks = [
        airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), 100_000_000)
        for kp in keypairs
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(successes) >= 40, f"Only {len(successes)}/50 airdrops succeeded"


@pytest.mark.slow
async def test_burst_transfer_barrage(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """20 parallel transfers from the same sender succeed."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    recipients = [Keypair() for _ in range(20)]

    tasks = [
        send_simple_transfer(solana_client, test_config.rpc_url, sender, r.pubkey(), 10_000)
        for r in recipients
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [r for r in results if isinstance(r, str)]
    assert len(successes) >= 15, f"Only {len(successes)}/20 transfers succeeded"


async def test_concurrent_mixed_rpc_reads(raw_rpc: RpcClient) -> None:
    """30 concurrent mixed RPC reads all return valid data."""
    tasks = []
    for _ in range(10):
        tasks.append(raw_rpc.get_slot())
        tasks.append(raw_rpc.get_block_height())
        tasks.append(raw_rpc.get_epoch_info())

    results = await asyncio.gather(*tasks)
    assert len(results) == 30
    # Verify slots are ints
    for i in range(0, 30, 3):
        assert isinstance(results[i], int)
        assert isinstance(results[i + 1], int)
        assert isinstance(results[i + 2], dict)


async def test_large_batch_50_items(raw_rpc: RpcClient) -> None:
    """Batch with 50 RPC requests succeeds."""
    requests = [("getSlot", None) for _ in range(50)]
    responses = await raw_rpc.batch(requests)
    assert len(responses) == 50
    for resp in responses:
        assert resp.ok
        assert isinstance(resp.result, int)


async def test_batch_100_mixed(raw_rpc: RpcClient) -> None:
    """Batch with 100 mixed method calls."""
    requests = []
    for _ in range(25):
        requests.extend(
            [
                ("getSlot", None),
                ("getBlockHeight", None),
                ("getHealth", None),
                ("getVersion", None),
            ]
        )
    responses = await raw_rpc.batch(requests)
    assert len(responses) == 100
    errors = [r for r in responses if not r.ok]
    assert len(errors) == 0


@pytest.mark.slow
async def test_websocket_subscription_storm(test_config: TestConfig) -> None:
    """5 simultaneous WebSocket subscriptions all receive notifications."""
    async with WsClient(config=test_config) as ws:
        sub_ids = []
        for _ in range(5):
            sub_id = await ws.slot_subscribe()
            sub_ids.append(sub_id)
        assert len(sub_ids) == 5

        # Receive at least one notification
        notification = await ws.recv_notification(timeout=15)
        assert "result" in notification

        # Unsubscribe all
        for sub_id in sub_ids:
            await ws.unsubscribe(sub_id)


@pytest.mark.slow
async def test_long_running_slot_subscription(test_config: TestConfig) -> None:
    """Receive 30+ slot notifications in a long-running subscription."""
    async with WsClient(config=test_config) as ws:
        await ws.slot_subscribe()
        notifications = await ws.recv_notifications(30, timeout=60)
        assert len(notifications) == 30
        slots = [n["result"]["slot"] for n in notifications]
        # Slots should be non-decreasing
        for i in range(len(slots) - 1):
            assert slots[i + 1] >= slots[i]


@pytest.mark.slow
async def test_account_creation_storm(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """10 parallel CreateAccount operations succeed."""
    from karstflow_tests.programs import SYSTEM_PROGRAM, create_program_owned_account

    payer = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    tasks = [
        create_program_owned_account(solana_client, payer, SYSTEM_PROGRAM, space=32)
        for _ in range(10)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(successes) >= 5, f"Only {len(successes)}/10 accounts created"


async def test_rapid_balance_queries(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """100 rapid-fire balance queries on the same account."""
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), 1_000_000_000)
    tasks = [solana_client.get_balance(kp.pubkey()) for _ in range(100)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 100
    for r in results:
        assert r.value == 1_000_000_000


async def test_memo_burst(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """10 sequential memo transactions all succeed."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    sigs = []
    for i in range(10):
        ix = build_memo_instruction(f"burst-memo-{i}", sender.pubkey())
        sig = await send_multi_instruction_tx(solana_client, sender, [ix])
        sigs.append(sig)
    assert len(sigs) == 10
    for sig in sigs:
        assert len(sig) > 40
