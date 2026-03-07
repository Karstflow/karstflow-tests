"""Functional tests: getClusterNodes."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_cluster_nodes_returns_list(rpc_client: RpcClient) -> None:
    """getClusterNodes returns at least one node."""
    nodes = await rpc_client.get_cluster_nodes()
    assert isinstance(nodes, list)
    assert len(nodes) >= 1


async def test_cluster_node_has_pubkey(rpc_client: RpcClient) -> None:
    """Each cluster node entry has a pubkey field."""
    nodes = await rpc_client.get_cluster_nodes()
    for node in nodes:
        assert "pubkey" in node
        assert isinstance(node["pubkey"], str)
        assert len(node["pubkey"]) >= 32


async def test_cluster_node_has_rpc(rpc_client: RpcClient) -> None:
    """At least one node reports an RPC address."""
    nodes = await rpc_client.get_cluster_nodes()
    rpc_nodes = [n for n in nodes if n.get("rpc") is not None]
    assert len(rpc_nodes) >= 1


async def test_cluster_node_has_gossip(rpc_client: RpcClient) -> None:
    """Cluster nodes have gossip addresses."""
    nodes = await rpc_client.get_cluster_nodes()
    for node in nodes:
        assert "gossip" in node
