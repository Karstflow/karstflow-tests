"""Functional tests: versioned transaction support (v0 transactions).

Tests that the validator correctly handles versioned transactions
and address lookup table references.
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.request_builder import RequestBuilder
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender, send_simple_transfer


async def test_get_block_with_tx_version(
    rpc_client: RpcClient,
) -> None:
    """getBlock with maxSupportedTransactionVersion=0 works."""
    slot = await rpc_client.get_slot()
    spec = (
        RequestBuilder("getBlock")
        .with_positional(slot)
        .with_encoding("json")
        .with_tx_version(0)
        .build()
    )
    result = await rpc_client.execute(spec)
    # May be null if slot is skipped
    if result is not None:
        assert "transactions" in result


async def test_get_transaction_with_version_support(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """getTransaction supports maxSupportedTransactionVersion."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
    )

    spec = (
        RequestBuilder("getTransaction")
        .with_positional(sig)
        .with_encoding("json")
        .with_tx_version(0)
        .with_commitment("confirmed")
        .build()
    )
    result = await rpc_client.execute(spec)
    assert result is not None
    assert "transaction" in result
    assert "meta" in result


async def test_get_block_json_parsed(
    rpc_client: RpcClient,
) -> None:
    """getBlock with jsonParsed encoding."""
    slot = await rpc_client.get_slot()
    spec = (
        RequestBuilder("getBlock")
        .with_positional(slot)
        .with_encoding("jsonParsed")
        .with_tx_version(0)
        .build()
    )
    result = await rpc_client.execute(spec)
    if result is not None:
        assert "transactions" in result


async def test_get_transaction_base64(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """getTransaction with base64 encoding returns raw bytes."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
    )

    spec = (
        RequestBuilder("getTransaction")
        .with_positional(sig)
        .with_encoding("base64")
        .with_tx_version(0)
        .with_commitment("confirmed")
        .build()
    )
    result = await rpc_client.execute(spec)
    assert result is not None
    tx_data = result["transaction"]
    assert isinstance(tx_data, list)
    assert tx_data[1] == "base64"


async def test_address_lookup_table_program_exists(
    rpc_client: RpcClient,
) -> None:
    """Address Lookup Table program account exists."""
    alt_program = "AddressLookupTab1e1111111111111111111111111"
    info = await rpc_client.get_account_info(alt_program)
    assert info is not None
    assert info["executable"] is True


async def test_get_block_rewards(
    rpc_client: RpcClient,
) -> None:
    """getBlock includes rewards field."""
    slot = await rpc_client.get_slot()
    block = await rpc_client.get_block(slot)
    if block is not None:
        assert "rewards" in block
        assert isinstance(block["rewards"], list)
