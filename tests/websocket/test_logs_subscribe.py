"""WebSocket tests: logsSubscribe notifications."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.factories import TransactionFactory
from karstflow_tests.wait import wait_for_confirmation
from karstflow_tests.ws import WsClient


async def test_logs_subscribe_all(ws: WsClient) -> None:
    """logsSubscribe('all') receives log notifications."""
    sub_id = await ws.logs_subscribe()
    assert isinstance(sub_id, int)

    notification = await ws.recv_notification(timeout=15.0)
    assert "result" in notification
    result = notification["result"]
    assert "value" in result
    value = result["value"]
    assert "signature" in value
    assert "logs" in value
    assert isinstance(value["logs"], list)


async def test_logs_subscribe_mentions_filter(
    ws: WsClient,
    solana_client: AsyncClient,
    test_config: TestConfig,
    tx_factory: TransactionFactory,
) -> None:
    """logsSubscribe with mentions filter captures relevant transactions."""
    sender = Keypair()
    resp = await solana_client.request_airdrop(sender.pubkey(), 5_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    # Subscribe to logs mentioning the sender
    await ws.logs_subscribe(mention=str(sender.pubkey()))

    # Trigger a transaction involving the sender
    recipient = Keypair()
    await tx_factory.send_transfer(sender, recipient.pubkey(), 100_000_000)

    notification = await ws.recv_notification(timeout=15.0)
    result = notification["result"]
    assert "value" in result
    value = result["value"]
    assert "signature" in value
    assert "logs" in value


async def test_logs_unsubscribe(ws: WsClient) -> None:
    """logsUnsubscribe properly removes subscription."""
    sub_id = await ws.logs_subscribe()
    await ws.recv_notification(timeout=15.0)
    result = await ws.unsubscribe(sub_id)
    assert result is True
