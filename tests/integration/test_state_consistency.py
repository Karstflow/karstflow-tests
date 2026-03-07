"""Integration tests: state consistency after operations.

Verifies that state changes propagate correctly across the cluster.
"""

from __future__ import annotations

import asyncio

import pytest
from solders.keypair import Keypair

from karstflow_tests.client import ValidatorClient

pytestmark = pytest.mark.integration


async def test_transaction_count_increases_all_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Transaction count increases on all nodes after activity."""
    counts_before = []
    for client in cluster_clients:
        info = await client.rpc.get_epoch_info()
        counts_before.append(info.get("transactionCount", 0))

    kp = Keypair()
    await cluster_clients[0].fund_account(kp.pubkey(), 1_000_000_000)
    await asyncio.sleep(3)

    counts_after = []
    for client in cluster_clients:
        info = await client.rpc.get_epoch_info()
        counts_after.append(info.get("transactionCount", 0))

    for i in range(len(cluster_clients)):
        assert counts_after[i] > counts_before[i], f"Node {i} tx count didn't increase"


async def test_block_height_advances_all_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Block height advances on all nodes."""
    heights_before = [await client.rpc.get_block_height() for client in cluster_clients]
    await asyncio.sleep(3)
    heights_after = [await client.rpc.get_block_height() for client in cluster_clients]

    for i in range(len(cluster_clients)):
        assert heights_after[i] > heights_before[i], f"Node {i} block height stalled"


async def test_supply_consistent_across_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Total supply is consistent across all nodes."""
    supplies = []
    for client in cluster_clients:
        supply = await client.rpc.get_supply()
        supplies.append(supply["value"]["total"])

    max_diff = max(supplies) - min(supplies)
    assert max_diff < 1_000_000_000, f"Supply divergence too high: {supplies}"


async def test_identity_unique_per_node(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Each node reports a unique identity."""
    identities = set()
    for client in cluster_clients:
        identity = await client.rpc.get_identity()
        identities.add(identity["identity"])
    assert len(identities) == len(cluster_clients)
