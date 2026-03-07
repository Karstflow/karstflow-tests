"""WebSocket tests: programSubscribe."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.ws import WsClient
from tests.helpers.constants import SYSTEM_PROGRAM
from tests.helpers.setup import airdrop_and_confirm


async def test_program_subscribe_system(
    ws: WsClient,
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """programSubscribe for system program triggers on new account funding."""
    sub_id = await ws.program_subscribe(SYSTEM_PROGRAM)
    assert sub_id >= 0

    # Create a new funded account (will trigger system program notification)
    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), 1_000_000_000)

    notification = await ws.recv_notification(timeout=15)
    assert "result" in notification
    result = notification["result"]
    assert "value" in result
    value = result["value"]
    assert "pubkey" in value
    assert "account" in value


async def test_program_subscribe_account_data(
    ws: WsClient,
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """programSubscribe notification includes account data."""
    await ws.program_subscribe(SYSTEM_PROGRAM)

    kp = Keypair()
    await airdrop_and_confirm(solana_client, test_config.rpc_url, kp.pubkey(), 500_000_000)

    notification = await ws.recv_notification(timeout=15)
    account = notification["result"]["value"]["account"]
    assert "lamports" in account
    assert "owner" in account
    assert "data" in account


async def test_program_unsubscribe(ws: WsClient) -> None:
    """programUnsubscribe succeeds."""
    sub_id = await ws.program_subscribe(SYSTEM_PROGRAM)
    result = await ws.unsubscribe(sub_id)
    assert result is True
