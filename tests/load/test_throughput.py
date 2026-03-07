"""Load tests: RPC throughput measurement via pytest-benchmark.

These tests measure how many RPC calls the validator can handle
per second under controlled conditions.
"""

from __future__ import annotations

import asyncio

import pytest
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient

pytestmark = [pytest.mark.load, pytest.mark.slow]


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _run_rpc_calls(rpc: RpcClient, method: str, count: int) -> int:
    """Run N RPC calls and return count of successes."""
    tasks = [rpc.request(method) for _ in range(count)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if not isinstance(r, Exception))


async def test_getslot_throughput(
    raw_rpc: RpcClient,
) -> None:
    """Measure getSlot throughput: 100 concurrent calls."""
    successes = await _run_rpc_calls(raw_rpc, "getSlot", 100)
    assert successes >= 90, f"Only {successes}/100 getSlot calls succeeded"


async def test_gethealth_throughput(
    raw_rpc: RpcClient,
) -> None:
    """Measure getHealth throughput: 100 concurrent calls."""
    successes = await _run_rpc_calls(raw_rpc, "getHealth", 100)
    assert successes >= 90


async def test_getversion_throughput(
    raw_rpc: RpcClient,
) -> None:
    """Measure getVersion throughput: 50 concurrent calls."""
    successes = await _run_rpc_calls(raw_rpc, "getVersion", 50)
    assert successes >= 45


async def test_batch_throughput(raw_rpc: RpcClient) -> None:
    """Measure batch RPC throughput: 10 batches of 10 calls each."""
    tasks = [raw_rpc.batch([("getSlot", None) for _ in range(10)]) for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = sum(1 for r in results if not isinstance(r, Exception))
    assert successes >= 8


async def test_getbalance_throughput(
    solana_client: AsyncClient,
    test_config: TestConfig,
) -> None:
    """Measure getBalance throughput: 50 concurrent calls."""
    kp = Keypair()
    tasks = [solana_client.get_balance(kp.pubkey()) for _ in range(50)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = sum(1 for r in results if not isinstance(r, Exception))
    assert successes >= 45


async def test_mixed_read_throughput(raw_rpc: RpcClient) -> None:
    """Mixed read-only calls: 100 total across 5 methods."""
    tasks = []
    for _ in range(20):
        tasks.append(raw_rpc.get_slot())
        tasks.append(raw_rpc.get_block_height())
        tasks.append(raw_rpc.get_health())
        tasks.append(raw_rpc.get_version())
        tasks.append(raw_rpc.get_epoch_info())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    successes = sum(1 for r in results if not isinstance(r, Exception))
    assert successes >= 90
