"""WebSocket tests: rootSubscribe."""

from __future__ import annotations

from karstflow_tests.ws import WsClient


async def test_root_subscribe_receives_notifications(ws: WsClient) -> None:
    """rootSubscribe receives root slot notifications."""
    sub_id = await ws.root_subscribe()
    assert sub_id >= 0

    notification = await ws.recv_notification(timeout=15)
    assert "result" in notification
    root_slot = notification["result"]
    assert isinstance(root_slot, int)
    assert root_slot >= 0


async def test_root_subscribe_multiple_notifications(ws: WsClient) -> None:
    """rootSubscribe receives multiple sequential notifications."""
    await ws.root_subscribe()

    notifications = await ws.recv_notifications(3, timeout=30)
    assert len(notifications) == 3
    roots = [n["result"] for n in notifications]
    # Roots should be non-decreasing
    for i in range(len(roots) - 1):
        assert roots[i + 1] >= roots[i]


async def test_root_unsubscribe(ws: WsClient) -> None:
    """rootUnsubscribe successfully unsubscribes."""
    sub_id = await ws.root_subscribe()
    result = await ws.unsubscribe(sub_id)
    assert result is True
