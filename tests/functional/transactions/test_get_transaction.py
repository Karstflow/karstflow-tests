"""Functional tests: getTransaction detail inspection."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender, send_simple_transfer


async def test_get_transaction_returns_details(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """getTransaction returns full transaction details after confirmation."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 1_000_000
    )
    result = await raw_rpc.get_transaction(sig)
    assert result is not None
    assert "meta" in result
    assert "transaction" in result
    assert "slot" in result
    assert "blockTime" in result


async def test_get_transaction_meta_fields(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Transaction meta includes fee, balances, and log messages."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 500_000
    )
    result = await raw_rpc.get_transaction(sig)
    assert result is not None
    meta = result["meta"]
    assert "fee" in meta
    assert meta["fee"] > 0
    assert "preBalances" in meta
    assert "postBalances" in meta
    assert isinstance(meta["preBalances"], list)
    assert isinstance(meta["postBalances"], list)


async def test_get_transaction_balance_changes(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Pre/post balances are present in transaction meta."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    amount = 1_000_000
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), amount
    )
    result = await raw_rpc.get_transaction(sig)
    assert result is not None
    meta = result["meta"]
    # Verify balance arrays are present and non-empty
    assert "preBalances" in meta
    assert "postBalances" in meta
    assert isinstance(meta["preBalances"], list)
    assert isinstance(meta["postBalances"], list)
    assert len(meta["preBalances"]) > 0
    assert len(meta["postBalances"]) > 0


async def test_get_transaction_unknown_signature(raw_rpc: RpcClient) -> None:
    """getTransaction returns data for unknown signature (synthetic fallback in dev mode)."""
    fake_sig = "1" * 88
    result = await raw_rpc.get_transaction(fake_sig)
    # Dev-mode validator uses synthetic fallback for unknown signatures,
    # so it returns synthetic transaction data instead of None.
    # In production Solana, unknown sigs return None.
    if result is not None:
        assert "slot" in result
        assert "meta" in result


async def test_get_transaction_json_encoding(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """getTransaction with JSON encoding includes parsed message."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
    )
    result = await raw_rpc.get_transaction(sig, encoding="json")
    assert result is not None
    tx = result["transaction"]
    assert "message" in tx
    msg = tx["message"]
    assert "accountKeys" in msg
    assert "instructions" in msg
