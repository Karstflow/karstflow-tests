"""Root fixtures: node, Solana RPC client, funded keypair."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.node import NodeHandle, NodeManager
from karstflow_tests.wait import wait_for_confirmation


def _get_rpc_url() -> str:
    """Resolve RPC URL from env or default."""
    return os.environ.get("KARSTFLOW_RPC_URL", "http://localhost:8899")


def _get_ws_url() -> str:
    """Resolve WebSocket URL from env or default."""
    return os.environ.get("KARSTFLOW_WS_URL", "ws://localhost:8900")


@pytest.fixture(scope="session")
def node_manager() -> NodeManager:
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
async def solana_client(node_handle: NodeHandle) -> AsyncClient:  # type: ignore[misc]
    """Provide the official Solana async RPC client."""
    client = AsyncClient(node_handle.rpc_url)
    yield client  # type: ignore[misc]
    await client.close()


@pytest_asyncio.fixture
async def funded_keypair(solana_client: AsyncClient) -> Keypair:
    """Create and return a funded keypair (10 SOL)."""
    kp = Keypair()
    resp = await solana_client.request_airdrop(kp.pubkey(), 10_000_000_000)
    await wait_for_confirmation(
        str(solana_client._provider.endpoint_uri),
        str(resp.value),
    )
    return kp
