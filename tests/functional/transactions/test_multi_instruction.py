"""Functional tests: Multi-instruction transactions."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.system_program import TransferParams, transfer

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import build_memo_instruction, send_multi_instruction_tx
from tests.helpers.setup import funded_sender


async def test_transfer_plus_memo(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transaction with transfer + memo instructions succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()

    transfer_ix = transfer(
        TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=recipient.pubkey(),
            lamports=1_000_000,
        )
    )
    memo_ix = build_memo_instruction("transfer note", sender.pubkey())
    sig = await send_multi_instruction_tx(solana_client, sender, [transfer_ix, memo_ix])
    assert len(sig) > 40
    balance = await solana_client.get_balance(recipient.pubkey())
    assert balance.value == 1_000_000


async def test_multiple_transfers_in_one_tx(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transaction with multiple transfer instructions to different recipients."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    recipients = [Keypair() for _ in range(5)]

    ixs = [
        transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=r.pubkey(),
                lamports=100_000,
            )
        )
        for r in recipients
    ]
    sig = await send_multi_instruction_tx(solana_client, sender, ixs)
    assert len(sig) > 40

    for r in recipients:
        bal = await solana_client.get_balance(r.pubkey())
        assert bal.value == 100_000


async def test_transfer_with_multiple_memos(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transaction with transfer + multiple memos."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()

    ixs = [
        transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=500_000,
            )
        ),
        build_memo_instruction("memo-1", sender.pubkey()),
        build_memo_instruction("memo-2", sender.pubkey()),
    ]
    sig = await send_multi_instruction_tx(solana_client, sender, ixs)
    assert len(sig) > 40
