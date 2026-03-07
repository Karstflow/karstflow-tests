"""WebSocket tests: error handling and edge cases."""

from __future__ import annotations

import pytest

from karstflow_tests.config import TestConfig
from karstflow_tests.ws import WsClient, WsError


async def test_subscribe_invalid_method(test_config: TestConfig) -> None:
    """Subscribing with invalid method name raises error."""
    async with WsClient(config=test_config) as ws:
        with pytest.raises(WsError):
            await ws.subscribe("totallyBogusSubscribe")


async def test_account_subscribe_invalid_pubkey(test_config: TestConfig) -> None:
    """Account subscribe with invalid pubkey raises error."""
    async with WsClient(config=test_config) as ws:
        with pytest.raises((WsError, Exception)):
            await ws.account_subscribe("not-a-valid-pubkey")


async def test_recv_timeout_no_notifications(test_config: TestConfig) -> None:
    """recv_notification times out when no subscription active."""
    async with WsClient(config=test_config) as ws:
        with pytest.raises(TimeoutError):
            await ws.recv_notification(timeout=1.0)


async def test_rapid_subscribe_unsubscribe_cycles(test_config: TestConfig) -> None:
    """Rapid subscribe/unsubscribe cycles don't crash."""
    async with WsClient(config=test_config) as ws:
        for _ in range(5):
            sub_id = await ws.slot_subscribe()
            await ws.unsubscribe(sub_id)


async def test_unsubscribe_after_close_safe(test_config: TestConfig) -> None:
    """Unsubscribing after close doesn't raise."""
    ws = WsClient(config=test_config)
    await ws.connect()
    sub_id = await ws.slot_subscribe()
    await ws.close()
    # Should be safe to call after close
    result = await ws.unsubscribe(sub_id)
    assert result is False
