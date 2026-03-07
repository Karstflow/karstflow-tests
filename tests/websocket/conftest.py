"""WebSocket test fixtures."""

import pytest
import pytest_asyncio

from karstflow_tests.node import NodeHandle
from karstflow_tests.ws import WsSubscription


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.websocket)


@pytest_asyncio.fixture
async def ws_subscription(node_handle: NodeHandle):
    sub = WsSubscription(node_handle.ws_url)
    await sub.connect()
    yield sub
    await sub.close()
