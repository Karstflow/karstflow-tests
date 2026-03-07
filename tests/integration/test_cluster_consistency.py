"""Integration tests: Multi-node cluster state consistency.

These tests require a running 3-node cluster (just cluster-up).
They verify that state is consistent across all nodes.
"""

from __future__ import annotations

import asyncio

import pytest
from solders.keypair import Keypair

from karstflow_tests.client import ValidatorClient

pytestmark = pytest.mark.integration


async def test_genesis_hash_matches_across_cluster(
    cluster_clients: list[ValidatorClient],
) -> None:
    """All nodes share the same genesis hash."""
    hashes = []
    for client in cluster_clients:
        h = await client.rpc.get_genesis_hash()
        hashes.append(h)
    assert len(set(hashes)) == 1, f"Genesis hash mismatch: {hashes}"


async def test_all_nodes_healthy(
    cluster_clients: list[ValidatorClient],
) -> None:
    """All nodes respond to health checks."""
    for i, client in enumerate(cluster_clients):
        healthy = await client.is_healthy()
        assert healthy, f"Node {i} is not healthy"


async def test_slot_convergence(
    cluster_clients: list[ValidatorClient],
) -> None:
    """All nodes are within a few slots of each other."""
    slots = []
    for client in cluster_clients:
        slot = await client.get_slot()
        slots.append(slot)
    max_diff = max(slots) - min(slots)
    assert max_diff < 10, f"Slot divergence too high: {slots} (diff={max_diff})"


async def test_cross_node_state_write_read(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Airdrop on node 0, verify balance on node 1."""
    kp = Keypair()
    await cluster_clients[0].fund_account(kp.pubkey(), 1_000_000_000)

    # Wait for propagation
    await asyncio.sleep(3)

    balance = await cluster_clients[1].get_balance(kp.pubkey())
    assert balance == 1_000_000_000


async def test_leader_schedule_consistent(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Leader schedule is the same across all nodes."""
    schedules = []
    for client in cluster_clients:
        s = await client.rpc.get_leader_schedule()
        schedules.append(s)
    # All should have the same validator set
    keys = [set(s.keys()) if s else set() for s in schedules]
    assert all(k == keys[0] for k in keys), f"Leader schedule mismatch: {keys}"


async def test_vote_accounts_visible_from_all_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Vote accounts are visible from all nodes."""
    for i, client in enumerate(cluster_clients):
        result = await client.rpc.get_vote_accounts()
        assert len(result["current"]) >= 1, f"Node {i} sees no vote accounts"


async def test_version_consistent(
    cluster_clients: list[ValidatorClient],
) -> None:
    """All nodes report the same software version."""
    versions = []
    for client in cluster_clients:
        v = await client.rpc.get_version()
        versions.append(v["solana-core"])
    assert len(set(versions)) == 1, f"Version mismatch: {versions}"


async def test_transfer_across_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Transfer initiated on node 0 is visible on node 2."""
    sender_kp = Keypair()
    recipient_kp = Keypair()

    await cluster_clients[0].fund_account(sender_kp.pubkey(), 5_000_000_000)
    await cluster_clients[0].transfer(sender_kp, recipient_kp.pubkey(), 1_000_000_000)

    await asyncio.sleep(3)

    balance = await cluster_clients[2].get_balance(recipient_kp.pubkey())
    assert balance == 1_000_000_000


async def test_epoch_info_close_across_nodes(
    cluster_clients: list[ValidatorClient],
) -> None:
    """Epoch info is consistent across nodes."""
    epochs = []
    for client in cluster_clients:
        info = await client.get_epoch_info()
        epochs.append(info.epoch)
    assert len(set(epochs)) == 1, f"Epoch mismatch: {epochs}"
