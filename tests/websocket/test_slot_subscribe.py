"""WebSocket tests: slotSubscribe notifications."""

from __future__ import annotations

from karstflow_tests.ws import WsClient


async def test_slot_subscribe_receives_notifications(ws: WsClient) -> None:
    """slotSubscribe receives slot update notifications."""
    sub_id = await ws.slot_subscribe()
    assert isinstance(sub_id, int)

    notification = await ws.recv_notification(timeout=15.0)
    assert "result" in notification
    result = notification["result"]
    assert "slot" in result
    assert "parent" in result
    assert isinstance(result["slot"], int)
    assert result["slot"] > 0


async def test_slot_subscribe_multiple_notifications(ws: WsClient) -> None:
    """Can receive multiple sequential slot notifications."""
    await ws.slot_subscribe()
    notifications = await ws.recv_notifications(count=3, timeout=15.0)
    assert len(notifications) == 3

    slots = [n["result"]["slot"] for n in notifications]
    # Slots should be non-decreasing (may repeat for same slot with different status)
    for i in range(1, len(slots)):
        assert slots[i] >= slots[i - 1]


async def test_slot_unsubscribe(ws: WsClient) -> None:
    """slotUnsubscribe properly removes subscription."""
    sub_id = await ws.slot_subscribe()
    # Receive one notification to confirm subscription is active
    await ws.recv_notification(timeout=15.0)
    # Unsubscribe
    result = await ws.unsubscribe(sub_id)
    assert result is True


async def test_slot_subscribe_status_field(ws: WsClient) -> None:
    """Slot notifications include root/status information."""
    await ws.slot_subscribe()
    notification = await ws.recv_notification(timeout=15.0)
    result = notification["result"]
    # Should have slot, parent, and root fields
    assert "slot" in result
    assert "parent" in result
    assert "root" in result
