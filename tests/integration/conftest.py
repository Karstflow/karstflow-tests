"""Integration test fixtures: multi-node cluster."""

import pytest
import pytest_asyncio

from karstflow_tests.node import NodeManager


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.integration)


@pytest_asyncio.fixture(scope="module")
async def cluster(node_manager: NodeManager):
    handle = await node_manager.start_cluster(
        compose_file="docker-compose.yml",
        nodes=3,
    )
    await handle.wait_all_ready(timeout=60)
    yield handle
    await handle.stop()
