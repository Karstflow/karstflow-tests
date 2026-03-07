"""Integration test fixtures: multi-node cluster."""

import pytest
import pytest_asyncio

from karstflow_tests.client import ValidatorClient
from karstflow_tests.config import TestConfig
from karstflow_tests.node import ClusterHandle, NodeManager


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.integration)


@pytest_asyncio.fixture(scope="module")
async def cluster(node_manager: NodeManager) -> ClusterHandle:  # type: ignore[misc]
    """Start and manage a 3-node cluster for integration tests."""
    handle = await node_manager.start_cluster(
        compose_file="docker-compose.yml",
        nodes=3,
    )
    await handle.wait_all_ready(timeout=60)
    yield handle  # type: ignore[misc]
    await handle.stop()


@pytest_asyncio.fixture
async def cluster_clients(
    cluster: ClusterHandle,
) -> list[ValidatorClient]:  # type: ignore[misc]
    """Provide ValidatorClient instances for each node in the cluster."""
    clients = []
    for node in cluster.nodes:
        cfg = TestConfig(rpc_url=node.rpc_url, ws_url=node.ws_url)  # type: ignore[call-arg]
        clients.append(ValidatorClient(config=cfg))
    yield clients  # type: ignore[misc]
    for c in clients:
        await c.close()
