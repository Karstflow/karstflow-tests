"""Functional tests: System program deep coverage.

Tests transfer edge cases, CreateAccount error conditions,
and system program instruction behavior in detail.
"""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solana.rpc.core import RPCException
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.programs import SYSTEM_PROGRAM, create_program_owned_account
from karstflow_tests.rpc import RpcClient
from tests.helpers.setup import (
    build_raw_transfer,
    funded_sender,
    send_simple_transfer,
)


async def test_transfer_exact_balance_minus_fee(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Transfer that leaves exactly 0 lamports (drain account)."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 1_000_000_000)
    recipient = Keypair()
    balance = (await solana_client.get_balance(sender.pubkey())).value

    # Need to estimate fee — transfer a small amount first to observe fee
    await send_simple_transfer(solana_client, test_config.rpc_url, sender, recipient.pubkey(), 1000)
    new_balance = (await solana_client.get_balance(sender.pubkey())).value
    fee = balance - new_balance - 1000

    # Now drain the rest
    remaining = new_balance
    drain_amount = remaining - fee
    if drain_amount > 0:
        await send_simple_transfer(
            solana_client, test_config.rpc_url, sender, recipient.pubkey(), drain_amount
        )
        final = (await solana_client.get_balance(sender.pubkey())).value
        assert final == 0


async def test_transfer_self_only_deducts_fee(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Self-transfer only deducts the transaction fee."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    balance_before = (await solana_client.get_balance(sender.pubkey())).value
    await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, sender.pubkey(), 1_000_000
    )
    balance_after = (await solana_client.get_balance(sender.pubkey())).value
    # Only fee should be deducted
    assert balance_before - balance_after > 0
    assert balance_before - balance_after < 100_000  # fee < 100k lamports


async def test_create_account_duplicate_pubkey_fails(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """CreateAccount with already-existing pubkey fails."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    acct = await create_program_owned_account(solana_client, payer, SYSTEM_PROGRAM, space=32)

    # Try to create again with the same pubkey — should fail
    from solders.message import Message
    from solders.system_program import CreateAccountParams, create_account
    from solders.transaction import Transaction

    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    rent_resp = await solana_client.get_minimum_balance_for_rent_exemption(32)

    ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=acct.pubkey(),
            lamports=rent_resp.value,
            space=32,
            owner=SYSTEM_PROGRAM,
        )
    )
    msg = Message.new_with_blockhash([ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, acct], blockhash)

    with pytest.raises(RPCException):
        await solana_client.send_transaction(tx)


async def test_create_account_zero_space(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """CreateAccount with zero space succeeds."""
    payer = await funded_sender(solana_client, test_config.rpc_url)
    acct = await create_program_owned_account(solana_client, payer, SYSTEM_PROGRAM, space=0)
    result = await solana_client.get_account_info(acct.pubkey())
    assert result.value is not None
    assert len(result.value.data) == 0


async def test_insufficient_funds_for_rent(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """CreateAccount with insufficient lamports for rent fails."""
    payer = await funded_sender(solana_client, test_config.rpc_url, 1_000_000)

    from solders.message import Message
    from solders.system_program import CreateAccountParams, create_account
    from solders.transaction import Transaction

    new_acct = Keypair()
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash

    # Provide way too few lamports for 10KB data
    ix = create_account(
        CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=new_acct.pubkey(),
            lamports=1,  # way too low
            space=10240,
            owner=SYSTEM_PROGRAM,
        )
    )
    msg = Message.new_with_blockhash([ix], payer.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([payer, new_acct], blockhash)

    with pytest.raises(RPCException):
        await solana_client.send_transaction(tx)


async def test_transfer_fee_via_rpc_inspection(
    solana_client: AsyncClient,
    test_config: TestConfig,
    raw_rpc: RpcClient,
) -> None:
    """Transaction fee is visible in getTransaction meta."""
    sender = await funded_sender(solana_client, test_config.rpc_url)
    recipient = Keypair()
    sig = await send_simple_transfer(
        solana_client, test_config.rpc_url, sender, recipient.pubkey(), 1_000_000
    )
    result = await raw_rpc.get_transaction(sig)
    assert result is not None
    fee = result["meta"]["fee"]
    assert isinstance(fee, int)
    assert fee > 0
    assert fee <= 5000  # dynamic rate, may decrease when idle


async def test_multiple_transfers_same_block(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Multiple transfers from same sender in rapid succession."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    recipients = [Keypair() for _ in range(5)]

    sigs = []
    for r in recipients:
        tx = await build_raw_transfer(solana_client, sender, r.pubkey(), 100_000)
        resp = await solana_client.send_transaction(tx)
        sigs.append(str(resp.value))

    # Confirm all
    from karstflow_tests.wait import wait_for_confirmation

    for sig in sigs:
        await wait_for_confirmation(test_config.rpc_url, sig)

    # Verify all received
    for r in recipients:
        bal = await solana_client.get_balance(r.pubkey())
        assert bal.value == 100_000
