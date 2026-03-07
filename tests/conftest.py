"""Root fixtures: node manager, RPC client, funded keypair."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio

from karstflow_tests.accounts import create_funded_keypair
from karstflow_tests.node import NodeHandle, NodeManager
from karstflow_tests.rpc import RpcClient


def _get_rpc_url() -> str:
    """Resolve RPC URL from env or default."""
    return os.environ.get("KARSTFLOW_RPC_URL", "http://localhost:8899")


def _get_ws_url() -> str:
    """Resolve WebSocket URL from env or default."""
    return os.environ.get("KARSTFLOW_WS_URL", "ws://localhost:8900")


@pytest.fixture(scope="session")
def node_manager():
    """Provide a NodeManager instance."""
    return NodeManager()


@pytest.fixture(scope="session")
def node_handle() -> NodeHandle:
    """Provide a handle to the running validator node.

    By default, assumes the node is already running externally.
    Set KARSTFLOW_AUTO_NODE=1 to start via Docker automatically.
    """
    return NodeHandle(
        rpc_url=_get_rpc_url(),
        ws_url=_get_ws_url(),
    )


@pytest_asyncio.fixture
async def rpc_client(node_handle: NodeHandle):
    """Provide an async RPC client connected to the validator."""
    client = RpcClient(node_handle.rpc_url)
    yield client
    await client.close()


@pytest_asyncio.fixture
async def funded_keypair(rpc_client: RpcClient):
    """Create and return a funded keypair (10 SOL)."""
    return await create_funded_keypair(rpc_client)
