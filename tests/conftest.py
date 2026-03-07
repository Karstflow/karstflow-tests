"""Root fixtures: config, clients, funded accounts, assertion helpers."""

from __future__ import annotations

import pytest
import pytest_asyncio
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.client import ValidatorClient
from karstflow_tests.config import TestConfig, load_config
from karstflow_tests.factories import KeypairFactory, TransactionFactory
from karstflow_tests.node import NodeHandle, NodeManager
from karstflow_tests.rpc import RpcClient
from karstflow_tests.state import StateCapture
from karstflow_tests.wait import wait_for_confirmation
from karstflow_tests.ws import WsClient

pytest_plugins = ["tests.plugins.rpc_coverage"]

# ── Configuration ────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_config() -> TestConfig:
    """Provide resolved test configuration."""
    return load_config()


# ── Node management ──────────────────────────────────────────────────


@pytest.fixture(scope="session")
def node_manager() -> NodeManager:
    """Provide a NodeManager instance."""
    return NodeManager()


@pytest.fixture(scope="session")
def node_handle(test_config: TestConfig) -> NodeHandle:
    """Provide a handle to the running validator node.

    Assumes the node is already running externally (via `just node-up`).
    """
    return NodeHandle(
        rpc_url=test_config.rpc_url,
        ws_url=test_config.ws_url,
    )


# ── Official Solana client ───────────────────────────────────────────


@pytest_asyncio.fixture
async def solana_client(test_config: TestConfig) -> AsyncClient:  # type: ignore[misc]
    """Provide the official Solana async RPC client."""
    client = AsyncClient(test_config.rpc_url)
    yield client  # type: ignore[misc]
    await client.close()


# ── Raw JSON-RPC client ─────────────────────────────────────────────


@pytest_asyncio.fixture
async def rpc_client(test_config: TestConfig) -> RpcClient:  # type: ignore[misc]
    """Provide raw JSON-RPC client for custom/batch requests."""
    client = RpcClient(config=test_config)
    yield client  # type: ignore[misc]
    await client.close()


# ── WebSocket client ─────────────────────────────────────────────────


@pytest_asyncio.fixture
async def ws_client(test_config: TestConfig) -> WsClient:  # type: ignore[misc]
    """Provide connected WebSocket client."""
    client = WsClient(config=test_config)
    await client.connect()
    yield client  # type: ignore[misc]
    await client.close()


# ── Unified test client ─────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_client(test_config: TestConfig) -> ValidatorClient:  # type: ignore[misc]
    """Provide the unified test client with all sub-clients."""
    client = ValidatorClient(config=test_config)
    yield client  # type: ignore[misc]
    await client.close()


# ── Cluster clients ──────────────────────────────────────────────────


@pytest_asyncio.fixture
async def cluster_clients(test_config: TestConfig) -> list[ValidatorClient]:  # type: ignore[misc]
    """Provide ValidatorClient instances for each node in a 3-node cluster.

    Expects KARSTFLOW_CLUSTER_URLS env var with comma-separated RPC URLs,
    falling back to default ports 8899, 8900, 8901.
    """
    import os

    urls_str = os.environ.get(
        "KARSTFLOW_CLUSTER_URLS",
        "http://localhost:8899,http://localhost:8909,http://localhost:8919",
    )
    urls = [u.strip() for u in urls_str.split(",")]

    clients = []
    for url in urls:
        cfg = TestConfig(rpc_url=url)
        clients.append(ValidatorClient(config=cfg))

    yield clients  # type: ignore[misc]

    for c in clients:
        await c.close()


# ── Raw RPC alias ────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def raw_rpc(test_config: TestConfig) -> RpcClient:  # type: ignore[misc]
    """Alias for rpc_client — used in load and stress tests."""
    client = RpcClient(config=test_config)
    yield client  # type: ignore[misc]
    await client.close()


# ── State capture ────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def state_capture(solana_client: AsyncClient, rpc_client: RpcClient) -> StateCapture:
    """Provide a StateCapture instance for before/after comparisons."""
    return StateCapture(solana_client, rpc_client)


# ── Factories ────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def keypair_factory(solana_client: AsyncClient) -> KeypairFactory:
    """Provide keypair factory bound to current client."""
    return KeypairFactory(solana_client)


@pytest_asyncio.fixture
async def tx_factory(solana_client: AsyncClient) -> TransactionFactory:
    """Provide transaction factory bound to current client."""
    return TransactionFactory(solana_client)


# ── Funded accounts ──────────────────────────────────────────────────


@pytest_asyncio.fixture
async def funded_keypair(solana_client: AsyncClient, test_config: TestConfig) -> Keypair:
    """Create and return a funded keypair (default 10 SOL)."""
    kp = Keypair()
    resp = await solana_client.request_airdrop(kp.pubkey(), test_config.airdrop_lamports)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))
    return kp


@pytest_asyncio.fixture
async def funded_keypair_pair(
    solana_client: AsyncClient, test_config: TestConfig
) -> tuple[Keypair, Keypair]:
    """Create two funded keypairs for transfer tests."""
    kp1, kp2 = Keypair(), Keypair()
    resp1 = await solana_client.request_airdrop(kp1.pubkey(), test_config.airdrop_lamports)
    resp2 = await solana_client.request_airdrop(kp2.pubkey(), test_config.airdrop_lamports)
    await wait_for_confirmation(test_config.rpc_url, str(resp1.value))
    await wait_for_confirmation(test_config.rpc_url, str(resp2.value))
    return kp1, kp2
