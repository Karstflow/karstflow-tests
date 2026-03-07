"""Functional tests: getTransactionCount."""

from __future__ import annotations

import asyncio

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender, send_simple_transfer


async def test_transaction_count_positive(raw_rpc: RpcClient) -> None:
    """getTransactionCount returns a positive integer."""
    count = await raw_rpc.get_transaction_count()
    assert isinstance(count, int)
    assert count >= 0


async def test_transaction_count_increases(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Transaction count increases after sending a transaction."""
    count_before = await raw_rpc.get_transaction_count()
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 1_000_000
    )
    await asyncio.sleep(1)
    count_after = await raw_rpc.get_transaction_count()
    assert count_after > count_before
