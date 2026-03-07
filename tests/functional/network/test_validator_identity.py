"""Functional tests: validator identity and cluster metadata.

Tests getIdentity, getClusterNodes details, and related metadata queries.
"""

from __future__ import annotations

import re

from karstflow_tests.rpc import RpcClient


async def test_identity_is_base58(rpc_client: RpcClient) -> None:
    """Validator identity is a valid base58 pubkey."""
    result = await rpc_client.get_identity()
    identity = result["identity"]
    assert isinstance(identity, str)
    assert len(identity) >= 32
    assert len(identity) <= 44
    # Base58 character set
    assert re.match(r"^[1-9A-HJ-NP-Za-km-z]+$", identity)


async def test_cluster_nodes_include_identity(rpc_client: RpcClient) -> None:
    """Cluster nodes list includes the validator's own identity."""
    identity = (await rpc_client.get_identity())["identity"]
    nodes = await rpc_client.get_cluster_nodes()
    node_pubkeys = [n["pubkey"] for n in nodes]
    assert identity in node_pubkeys


async def test_cluster_node_has_rpc_field(rpc_client: RpcClient) -> None:
    """At least one cluster node has an RPC endpoint."""
    nodes = await rpc_client.get_cluster_nodes()
    rpc_nodes = [n for n in nodes if n.get("rpc") is not None]
    assert len(rpc_nodes) >= 1


async def test_cluster_node_has_version(rpc_client: RpcClient) -> None:
    """Cluster nodes report their software version."""
    nodes = await rpc_client.get_cluster_nodes()
    for node in nodes:
        assert "version" in node
        assert node["version"] is not None


async def test_cluster_node_has_tpu(rpc_client: RpcClient) -> None:
    """At least one cluster node has a TPU address."""
    nodes = await rpc_client.get_cluster_nodes()
    tpu_nodes = [n for n in nodes if n.get("tpu") is not None]
    assert len(tpu_nodes) >= 1


async def test_slot_leader_is_base58(rpc_client: RpcClient) -> None:
    """getSlotLeader returns a valid base58 pubkey."""
    leader = await rpc_client.get_slot_leader()
    assert isinstance(leader, str)
    assert len(leader) >= 32
    assert re.match(r"^[1-9A-HJ-NP-Za-km-z]+$", leader)


async def test_slot_leader_matches_identity_in_test_validator(
    rpc_client: RpcClient,
) -> None:
    """In a test validator, slot leader should match identity."""
    identity = (await rpc_client.get_identity())["identity"]
    leader = await rpc_client.get_slot_leader()
    assert leader == identity


async def test_version_has_solana_core(rpc_client: RpcClient) -> None:
    """getVersion includes solana-core field."""
    version = await rpc_client.get_version()
    assert "solana-core" in version
    # Version should be semver-like
    core = version["solana-core"]
    assert "." in core
