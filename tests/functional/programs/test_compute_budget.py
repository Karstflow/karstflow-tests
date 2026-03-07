"""Functional tests: ComputeBudget program (set units, priority fees)."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import (
    build_compute_budget_set_price,
    build_compute_budget_set_units,
    send_multi_instruction_tx,
)
from tests.helpers.setup import funded_sender


async def test_set_compute_unit_limit(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transaction with SetComputeUnitLimit succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()

    cu_ix = build_compute_budget_set_units(200_000)
    transfer_ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=recipient.pubkey(),
            lamports=100_000,
        )
    )
    sig = await send_multi_instruction_tx(solana_client, sender, [cu_ix, transfer_ix])
    assert len(sig) > 40

    balance = await solana_client.get_balance(recipient.pubkey())
    assert balance.value == 100_000


async def test_set_compute_unit_price(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transaction with priority fee (SetComputeUnitPrice) succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()

    price_ix = build_compute_budget_set_price(1_000)  # 1000 micro-lamports
    transfer_ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=recipient.pubkey(),
            lamports=100_000,
        )
    )
    sig = await send_multi_instruction_tx(solana_client, sender, [price_ix, transfer_ix])
    assert len(sig) > 40


async def test_set_both_compute_budget_params(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transaction with both compute unit limit and price succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()

    cu_ix = build_compute_budget_set_units(150_000)
    price_ix = build_compute_budget_set_price(500)
    transfer_ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=recipient.pubkey(),
            lamports=50_000,
        )
    )
    sig = await send_multi_instruction_tx(solana_client, sender, [cu_ix, price_ix, transfer_ix])
    assert len(sig) > 40
    balance = await solana_client.get_balance(recipient.pubkey())
    assert balance.value == 50_000
