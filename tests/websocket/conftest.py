"""WebSocket test fixtures."""

import pytest
import pytest_asyncio

from karstflow_tests.config import TestConfig
from karstflow_tests.ws import WsClient


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.websocket)


@pytest_asyncio.fixture
async def ws(test_config: TestConfig) -> WsClient:  # type: ignore[misc]
    """Provide a connected WebSocket client for subscription tests."""
    async with WsClient(config=test_config) as client:
        yield client  # type: ignore[misc]
