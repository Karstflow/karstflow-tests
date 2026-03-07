"""Functional test fixtures: single-node RPC method coverage."""

import pytest
import pytest_asyncio
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.wait import wait_for_confirmation


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.functional)


@pytest_asyncio.fixture
async def raw_rpc(test_config: TestConfig) -> RpcClient:  # type: ignore[misc]
    """Provide raw JSON-RPC client scoped to functional tests."""
    async with RpcClient(config=test_config) as client:
        yield client  # type: ignore[misc]


@pytest_asyncio.fixture
async def funded_account(
    solana_client,
    test_config: TestConfig,
) -> Keypair:
    """A funded account for functional tests (5 SOL)."""
    kp = Keypair()
    resp = await solana_client.request_airdrop(kp.pubkey(), 5_000_000_000)
    await wait_for_confirmation(test_config.rpc_url, str(resp.value))
    return kp
