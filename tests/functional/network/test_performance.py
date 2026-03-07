"""Functional tests: getRecentPerformanceSamples, getIdentity."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_recent_performance_samples(rpc_client: RpcClient) -> None:
    """getRecentPerformanceSamples returns sample data."""
    samples = await rpc_client.get_recent_performance_samples(limit=5)
    assert isinstance(samples, list)
    if samples:
        sample = samples[0]
        assert "slot" in sample
        assert "numTransactions" in sample
        assert "numSlots" in sample
        assert "samplePeriodSecs" in sample


async def test_performance_sample_fields(rpc_client: RpcClient) -> None:
    """Performance samples have consistent numeric fields."""
    samples = await rpc_client.get_recent_performance_samples(limit=3)
    for sample in samples:
        assert isinstance(sample["slot"], int)
        assert isinstance(sample["numTransactions"], int)
        assert sample["numTransactions"] >= 0
        assert isinstance(sample["numSlots"], int)
        assert sample["numSlots"] > 0


async def test_get_identity(rpc_client: RpcClient) -> None:
    """getIdentity returns the validator's pubkey."""
    result = await rpc_client.get_identity()
    assert "identity" in result
    assert isinstance(result["identity"], str)
    assert len(result["identity"]) >= 32


async def test_identity_consistent(rpc_client: RpcClient) -> None:
    """Validator identity is stable across requests."""
    id1 = (await rpc_client.get_identity())["identity"]
    id2 = (await rpc_client.get_identity())["identity"]
    assert id1 == id2


async def test_identity_in_cluster_nodes(rpc_client: RpcClient) -> None:
    """Validator identity appears in getClusterNodes."""
    identity = (await rpc_client.get_identity())["identity"]
    nodes = await rpc_client.get_cluster_nodes()
    node_pubkeys = [n["pubkey"] for n in nodes]
    assert identity in node_pubkeys
