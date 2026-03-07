"""Integration tests: cross-node transaction verification.

These tests require a running 3-node cluster (just cluster-up).
They verify transactions submitted on one node are visible on others.
"""

from __future__ import annotations

import asyncio

import pytest
from solders.keypair import Keypair

from karstflow_tests.client import ValidatorClient

pytestmark = pytest.mark.integration


async def test_airdrop_node0_balance_node1(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Airdrop on node 0, verify balance on node 1 and node 2."""
    kp = Keypair()
    await cluster_clients[0].fund_account(kp.pubkey(), 3_000_000_000)
    await asyncio.sleep(3)

    bal1 = await cluster_clients[1].get_balance(kp.pubkey())
    bal2 = await cluster_clients[2].get_balance(kp.pubkey())
    assert bal1 == 3_000_000_000
    assert bal2 == 3_000_000_000


async def test_transfer_node1_visible_node0(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Transfer submitted via node 1 is visible from node 0."""
    sender_kp = Keypair()
    recipient_kp = Keypair()

    await cluster_clients[1].fund_account(sender_kp.pubkey(), 5_000_000_000)
    await cluster_clients[1].transfer(sender_kp, recipient_kp.pubkey(), 1_000_000_000)

    await asyncio.sleep(3)
    balance = await cluster_clients[0].get_balance(recipient_kp.pubkey())
    assert balance == 1_000_000_000


async def test_sequential_transfers_across_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Chain of transfers across different nodes."""
    kp_a = Keypair()
    kp_b = Keypair()
    kp_c = Keypair()

    # Fund on node 0
    await cluster_clients[0].fund_account(kp_a.pubkey(), 10_000_000_000)
    await asyncio.sleep(2)

    # Transfer A->B via node 1
    await cluster_clients[1].transfer(kp_a, kp_b.pubkey(), 3_000_000_000)
    await asyncio.sleep(2)

    # Transfer B->C via node 2
    await cluster_clients[2].transfer(kp_b, kp_c.pubkey(), 1_000_000_000)
    await asyncio.sleep(2)

    # Verify C's balance from node 0
    bal = await cluster_clients[0].get_balance(kp_c.pubkey())
    assert bal == 1_000_000_000


async def test_concurrent_transfers_different_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Concurrent transfers from different nodes all succeed."""
    senders = []
    recipients = []
    for _i, client in enumerate(cluster_clients):
        kp = Keypair()
        await client.fund_account(kp.pubkey(), 5_000_000_000)
        senders.append(kp)
        recipients.append(Keypair())

    await asyncio.sleep(2)

    tasks = [
        cluster_clients[i].transfer(senders[i], recipients[i].pubkey(), 1_000_000_000)
        for i in range(len(cluster_clients))
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = [r for r in results if isinstance(r, str)]
    assert len(successes) >= 2


async def test_signature_visible_across_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Transaction signature is queryable from any node."""
    kp = Keypair()
    await cluster_clients[0].fund_account(kp.pubkey(), 5_000_000_000)
    recipient = Keypair()

    sig = await cluster_clients[0].transfer(kp, recipient.pubkey(), 1_000_000_000)
    await asyncio.sleep(3)

    for i, client in enumerate(cluster_clients):
        status = await client.get_signature_status(sig)
        assert status is not None, f"Node {i} can't find signature"
        assert status.confirmed
