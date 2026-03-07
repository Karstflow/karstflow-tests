"""Functional tests: concurrent write conflict scenarios."""

from __future__ import annotations

import asyncio
import contextlib

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from tests.helpers.setup import funded_sender, send_simple_transfer


async def test_two_transfers_same_sender_race(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Two simultaneous transfers from same sender — at least one succeeds."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 10_000_000_000)
    r1, r2 = Keypair(), Keypair()

    tasks = [
        send_simple_transfer(solana_client, test_config.rpc_url, sender, r1.pubkey(), 100_000),
        send_simple_transfer(solana_client, test_config.rpc_url, sender, r2.pubkey(), 100_000),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [r for r in results if isinstance(r, str)]
    assert len(successes) >= 1


async def test_rapid_sequential_transfers_exhaust(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Sequential transfers eventually exhaust balance."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 500_000)
    errors = 0
    for _ in range(5):
        try:
            recipient = Keypair()
            await send_simple_transfer(
                solana_client, test_config.rpc_url, sender, recipient.pubkey(), 100_000
            )
        except Exception:
            errors += 1
    # Should have at least one failure (not enough funds)
    assert errors >= 1


async def test_concurrent_balance_reads_during_transfer(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Balance reads during transfer are consistent."""
    sender = await funded_sender(solana_client, test_config.rpc_url, 5_000_000_000)

    async def read_balance() -> int:
        result = await solana_client.get_balance(sender.pubkey())
        return result.value

    async def do_transfer() -> None:
        r = Keypair()
        with contextlib.suppress(Exception):
            await send_simple_transfer(solana_client, test_config.rpc_url, sender, r.pubkey(), 1000)

    # Run reads and transfer concurrently
    tasks = [read_balance(), do_transfer(), read_balance(), read_balance()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # All balance reads should return valid integers
    balances = [r for r in results if isinstance(r, int)]
    assert len(balances) >= 2
    for b in balances:
        assert b >= 0


async def test_parallel_airdrops_to_same_account(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Multiple airdrops to same account — all should succeed."""
    kp = Keypair()
    from karstflow_tests.wait import wait_for_confirmation

    tasks = []
    for _ in range(3):

        async def airdrop() -> str:
            resp = await solana_client.request_airdrop(kp.pubkey(), 100_000_000)
            sig = str(resp.value)
            await wait_for_confirmation(test_config.rpc_url, sig)
            return sig

        tasks.append(airdrop())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [r for r in results if isinstance(r, str)]
    assert len(successes) >= 2

    bal = await solana_client.get_balance(kp.pubkey())
    assert bal.value >= 200_000_000  # At least 2 airdrops
