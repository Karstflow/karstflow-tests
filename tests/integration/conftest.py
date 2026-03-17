"""Integration test fixtures: multi-node cluster.

Supports two modes:
1. Docker-based: uses NodeManager to start cluster via docker-compose
2. External: uses KARSTFLOW_CLUSTER_URLS env var for pre-started nodes
"""

import os

import pytest
import pytest_asyncio

from karstflow_tests.client import ValidatorClient
from karstflow_tests.config import TestConfig
from karstflow_tests.node import ClusterHandle


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.integration)


@pytest_asyncio.fixture(scope="module")
async def cluster() -> ClusterHandle:  # type: ignore[misc]
    """Provide a cluster handle for integration tests.

    When KARSTFLOW_CLUSTER_URLS is set, connects to pre-running nodes.
    Otherwise, starts a 3-node cluster via docker-compose.
    """
    urls_env = os.environ.get("KARSTFLOW_CLUSTER_URLS", "")
    if urls_env:
        urls = [u.strip() for u in urls_env.split(",") if u.strip()]
        handle = ClusterHandle.from_urls(urls)
        await handle.wait_all_ready(timeout=15)
        yield handle  # type: ignore[misc]
        return

    from karstflow_tests.node import NodeManager

    mgr = NodeManager()
    handle = await mgr.start_cluster(compose_file="docker-compose.yml", nodes=3)
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
