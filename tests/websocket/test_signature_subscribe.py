"""WebSocket tests: signatureSubscribe."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.ws import WsClient
from tests.helpers.setup import funded_sender, send_simple_transfer


async def test_signature_subscribe_confirms(
    ws: WsClient,
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """signatureSubscribe notifies when transaction confirms."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()

    # Send transaction without waiting for confirmation
    from tests.helpers.setup import build_raw_transfer

    tx = await build_raw_transfer(solana_client, sender, recipient.pubkey(), 1_000_000)
    resp = await solana_client.send_transaction(tx)
    sig = str(resp.value)

    # Subscribe to the signature
    sub_id = await ws.signature_subscribe(sig)
    assert sub_id >= 0

    # Wait for confirmation notification
    notification = await ws.recv_notification(timeout=30)
    assert "result" in notification
    result = notification["result"]
    assert "value" in result
    value = result["value"]
    # Should indicate success (err is null)
    assert value.get("err") is None


async def test_signature_unsubscribe(
    ws: WsClient,
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """signatureUnsubscribe succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
    )
    sub_id = await ws.signature_subscribe(sig)
    result = await ws.unsubscribe(sub_id)
    assert result is True
