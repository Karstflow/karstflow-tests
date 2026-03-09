"""Functional tests: transaction simulation error conditions.

Tests various failure modes via simulateTransaction to verify
the validator returns appropriate error information.
"""

from __future__ import annotations

import base64

import httpx
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.message import Message
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender


async def _build_unsigned_transfer(
    client: AsyncClient,
    sender: Keypair,
    recipient: Keypair,
    lamports: int,
) -> Transaction:
    """Build a transfer transaction (signed)."""
    bh = await client.get_latest_blockhash()
    ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=recipient.pubkey(),
            lamports=lamports,
        )
    )
    msg = Message.new_with_blockhash([ix], sender.pubkey(), bh.value.blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([sender], bh.value.blockhash)
    return tx


async def test_simulate_successful_transfer(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulating a valid transfer succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    tx = await _build_unsigned_transfer(solana_client, sender, recipient, 100_000)

    tx_bytes = bytes(tx)
    tx_b64 = base64.b64encode(tx_bytes).decode()

    result = await rpc_client.simulate_transaction(tx_b64)
    value = result["value"]
    assert value["err"] is None


async def test_simulate_insufficient_funds(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulating transfer with insufficient funds returns error."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 100_000)
    recipient = Keypair()
    tx = await _build_unsigned_transfer(solana_client, sender, recipient, 1_000_000_000)

    tx_bytes = bytes(tx)
    tx_b64 = base64.b64encode(tx_bytes).decode()

    result = await rpc_client.simulate_transaction(tx_b64)
    value = result["value"]
    assert value["err"] is not None


async def test_simulate_returns_logs(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulation result includes transaction logs."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    tx = await _build_unsigned_transfer(solana_client, sender, recipient, 100_000)

    tx_bytes = bytes(tx)
    tx_b64 = base64.b64encode(tx_bytes).decode()

    result = await rpc_client.simulate_transaction(tx_b64)
    value = result["value"]
    assert "logs" in value
    assert isinstance(value["logs"], list)
    assert len(value["logs"]) > 0


async def test_simulate_returns_units_consumed(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulation result includes compute units consumed."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    tx = await _build_unsigned_transfer(solana_client, sender, recipient, 100_000)

    tx_bytes = bytes(tx)
    tx_b64 = base64.b64encode(tx_bytes).decode()

    result = await rpc_client.simulate_transaction(tx_b64)
    value = result["value"]
    assert "unitsConsumed" in value
    assert isinstance(value["unitsConsumed"], int)
    assert value["unitsConsumed"] > 0


async def test_simulate_returns_accounts(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulation can return post-simulation account states."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    tx = await _build_unsigned_transfer(solana_client, sender, recipient, 100_000)

    tx_bytes = bytes(tx)
    tx_b64 = base64.b64encode(tx_bytes).decode()

    # Use raw request to pass accounts option
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "simulateTransaction",
        "params": [
            tx_b64,
            {
                "encoding": "base64",
                "accounts": {
                    "encoding": "base64",
                    "addresses": [str(sender.pubkey())],
                },
            },
        ],
    }
    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.post(rpc_client.url, json=payload)
        data = resp.json()

    result = data["result"]["value"]
    assert result["err"] is None
    assert "accounts" in result
    assert len(result["accounts"]) == 1
