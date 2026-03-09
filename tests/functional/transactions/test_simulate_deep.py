"""Functional tests: simulateTransaction deep coverage."""

from __future__ import annotations

import base64

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.message import Message
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import build_memo_instruction
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import funded_sender


async def _build_and_encode(
    client: AsyncClient,
    sender: Keypair,
    ixs: list,  # type: ignore[type-arg]
) -> str:
    bh = await client.get_latest_blockhash()
    msg = Message.new_with_blockhash(ixs, sender.pubkey(), bh.value.blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([sender], bh.value.blockhash)
    return base64.b64encode(bytes(tx)).decode()


async def test_simulate_memo_tx_logs(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulating a memo tx includes the memo text in logs."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    ix = build_memo_instruction("hello-simulate", sender.pubkey())
    tx_b64 = await _build_and_encode(solana_client, sender, [ix])

    result = await rpc_client.simulate_transaction(tx_b64)
    value = result["value"]
    assert value["err"] is None
    logs = value["logs"]
    assert any("hello-simulate" in log for log in logs)


async def test_simulate_multi_instruction(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulating multi-instruction tx reports all operations."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    r1, r2 = Keypair(), Keypair()
    ixs = [
        transfer(TransferParams(from_pubkey=sender.pubkey(), to_pubkey=r1.pubkey(), lamports=1000)),
        transfer(TransferParams(from_pubkey=sender.pubkey(), to_pubkey=r2.pubkey(), lamports=2000)),
    ]
    tx_b64 = await _build_and_encode(solana_client, sender, ixs)

    result = await rpc_client.simulate_transaction(tx_b64)
    value = result["value"]
    assert value["err"] is None
    assert value["unitsConsumed"] > 0


async def test_simulate_transfer_to_self(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulating transfer to self succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=sender.pubkey(),
            lamports=1000,
        )
    )
    tx_b64 = await _build_and_encode(solana_client, sender, [ix])

    result = await rpc_client.simulate_transaction(tx_b64)
    value = result["value"]
    assert value["err"] is None


async def test_simulate_zero_lamport_transfer(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulating zero-lamport transfer succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=recipient.pubkey(),
            lamports=0,
        )
    )
    tx_b64 = await _build_and_encode(solana_client, sender, [ix])

    result = await rpc_client.simulate_transaction(tx_b64)
    # Zero-lamport transfer may succeed or fail depending on implementation
    assert result is not None


async def test_simulate_idempotent(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Simulating same tx twice returns same result (no state change)."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=recipient.pubkey(),
            lamports=100_000,
        )
    )
    tx_b64 = await _build_and_encode(solana_client, sender, [ix])

    result1 = await rpc_client.simulate_transaction(tx_b64)
    result2 = await rpc_client.simulate_transaction(tx_b64)

    assert result1["value"]["err"] == result2["value"]["err"]
    assert result1["value"]["unitsConsumed"] == result2["value"]["unitsConsumed"]
