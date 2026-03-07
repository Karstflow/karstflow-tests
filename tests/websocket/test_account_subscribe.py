"""WebSocket tests: accountSubscribe notifications."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.wait import wait_for_confirmation
from karstflow_tests.ws import WsClient


async def test_account_subscribe_on_airdrop(
    ws: WsClient,
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """accountSubscribe fires when account receives airdrop."""
    kp = Keypair()

    sub_id = await ws.account_subscribe(str(kp.pubkey()))
    assert isinstance(sub_id, int)

    # Trigger account change via airdrop
    resp = await solana_client.request_airdrop(kp.pubkey(), 1_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    notification = await ws.recv_notification(timeout=15.0)
    assert "result" in notification
    result = notification["result"]
    assert "value" in result
    value = result["value"]
    assert "lamports" in value
    assert value["lamports"] == 1_000_000_000


async def test_account_subscribe_on_transfer(
    ws: WsClient,
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """accountSubscribe fires when account balance changes via transfer."""
    sender = Keypair()
    recipient = Keypair()
    resp = await solana_client.request_airdrop(sender.pubkey(), 5_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    # Subscribe to recipient account changes
    await ws.account_subscribe(str(recipient.pubkey()))

    # Fund recipient to create the account first
    resp = await solana_client.request_airdrop(recipient.pubkey(), 1_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))

    notification = await ws.recv_notification(timeout=15.0)
    result = notification["result"]
    assert "value" in result
    assert result["value"]["lamports"] > 0


async def test_account_unsubscribe(
    ws: WsClient,
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """accountUnsubscribe properly removes subscription."""
    kp = Keypair()
    sub_id = await ws.account_subscribe(str(kp.pubkey()))

    # Trigger notification
    resp = await solana_client.request_airdrop(kp.pubkey(), 1_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))
    await ws.recv_notification(timeout=15.0)

    result = await ws.unsubscribe(sub_id)
    assert result is True
