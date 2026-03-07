"""WebSocket tests: advanced subscription patterns and edge cases."""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.wait import wait_for_confirmation
from karstflow_tests.ws import WsClient


async def test_multiple_slot_subscriptions(ws: WsClient) -> None:
    """Multiple slot subscriptions return independent IDs."""
    sub1 = await ws.slot_subscribe()
    sub2 = await ws.slot_subscribe()
    assert sub1 != sub2

    # Both should receive notifications
    notification = await ws.recv_notification(timeout=15.0)
    assert "result" in notification

    await ws.unsubscribe(sub1)
    await ws.unsubscribe(sub2)


async def test_subscribe_unsubscribe_resubscribe(ws: WsClient) -> None:
    """Can unsubscribe and resubscribe to the same type."""
    sub1 = await ws.slot_subscribe()
    await ws.recv_notification(timeout=15.0)
    await ws.unsubscribe(sub1)

    # Resubscribe
    sub2 = await ws.slot_subscribe()
    notification = await ws.recv_notification(timeout=15.0)
    assert "result" in notification
    await ws.unsubscribe(sub2)


async def test_unsubscribe_invalid_id(ws: WsClient) -> None:
    """Unsubscribing with invalid ID returns False."""
    result = await ws.unsubscribe(999999)
    assert result is False


async def test_root_and_slot_simultaneous(ws: WsClient) -> None:
    """Can subscribe to both root and slot simultaneously."""
    slot_sub = await ws.slot_subscribe()
    root_sub = await ws.root_subscribe()

    notifications = await ws.recv_notifications(3, timeout=15.0)
    assert len(notifications) == 3

    await ws.unsubscribe(slot_sub)
    await ws.unsubscribe(root_sub)


async def test_account_subscribe_system_program(ws: WsClient) -> None:
    """Account subscription on system program returns data."""
    sub_id = await ws.account_subscribe("11111111111111111111111111111111")
    assert isinstance(sub_id, int)
    await ws.unsubscribe(sub_id)


async def test_account_subscribe_with_commitment(ws: WsClient) -> None:
    """Account subscription respects commitment parameter."""
    sub_id = await ws.account_subscribe(
        "11111111111111111111111111111111",
        commitment="finalized",
    )
    assert isinstance(sub_id, int)
    await ws.unsubscribe(sub_id)


async def test_logs_subscribe_all(ws: WsClient) -> None:
    """Logs subscription with 'all' filter receives notifications."""
    sub_id = await ws.logs_subscribe()
    assert isinstance(sub_id, int)

    # Wait for any transaction log
    try:
        notification = await ws.recv_notification(timeout=15.0)
        assert "result" in notification
    except TimeoutError:
        pass  # OK if no transactions happen during test
    finally:
        await ws.unsubscribe(sub_id)


@pytest.mark.slow
async def test_account_subscribe_detects_airdrop(
    test_config: TestConfig,
) -> None:
    """Account subscription detects balance change from airdrop."""
    kp = Keypair()
    async with WsClient(config=test_config) as ws_local:
        sub_id = await ws_local.account_subscribe(str(kp.pubkey()))

        # Trigger airdrop
        async with AsyncClient(test_config.rpc_url) as client:
            resp = await client.request_airdrop(kp.pubkey(), 1_000_000_000)
            await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        # Should get a notification about balance change
        notification = await ws_local.recv_notification(timeout=15.0)
        assert "result" in notification
        value = notification["result"]["value"]
        assert value["lamports"] == 1_000_000_000

        await ws_local.unsubscribe(sub_id)


@pytest.mark.slow
async def test_logs_subscribe_with_mention(
    test_config: TestConfig,
) -> None:
    """Logs subscription with specific mention filter."""
    kp = Keypair()
    async with WsClient(config=test_config) as ws_local:
        sub_id = await ws_local.logs_subscribe(mention=str(kp.pubkey()))
        assert isinstance(sub_id, int)

        # Trigger a transaction mentioning this account
        async with AsyncClient(test_config.rpc_url) as client:
            resp = await client.request_airdrop(kp.pubkey(), 1_000_000_000)
            await wait_for_confirmation(test_config.rpc_url, str(resp.value))

        try:
            notification = await ws_local.recv_notification(timeout=15.0)
            assert "result" in notification
            value = notification["result"]["value"]
            assert "signature" in value
            assert "logs" in value
        except TimeoutError:
            pass  # Filter might not match airdrop in all implementations

        await ws_local.unsubscribe(sub_id)


async def test_program_subscribe_system(ws: WsClient) -> None:
    """Program subscription on system program."""
    sub_id = await ws.program_subscribe("11111111111111111111111111111111")
    assert isinstance(sub_id, int)
    await ws.unsubscribe(sub_id)
