"""Functional tests: parametrized RPC method sweep.

Verifies all known RPC methods respond without crashing.
"""

from __future__ import annotations

import pytest

from karstflow_tests.rpc import RpcClient

# Methods that need no params or accept empty params
_NO_PARAM_METHODS = [
    "getBlockHeight",
    "getClusterNodes",
    "getEpochInfo",
    "getEpochSchedule",
    "getFirstAvailableBlock",
    "getGenesisHash",
    "getHealth",
    "getHighestSnapshotSlot",
    "getIdentity",
    "getInflationGovernor",
    "getInflationRate",
    "getMaxRetransmitSlot",
    "getMaxShredInsertSlot",
    "getSlot",
    "getSlotLeader",
    "getStakeMinimumDelegation",
    "getSupply",
    "getTransactionCount",
    "getVersion",
    "getVoteAccounts",
    "minimumLedgerSlot",
]


@pytest.mark.parametrize("method", _NO_PARAM_METHODS, ids=_NO_PARAM_METHODS)
async def test_no_param_method_responds(rpc_client: RpcClient, method: str) -> None:
    """Each no-param RPC method responds without crashing."""
    resp = await rpc_client.request_raw(method)
    assert resp.ok, f"{method} returned error: {resp.error}"


async def test_all_methods_in_batch(rpc_client: RpcClient) -> None:
    """Send all no-param methods in a single batch — all respond."""
    requests = [(method, None) for method in _NO_PARAM_METHODS]
    responses = await rpc_client.batch(requests)
    assert len(responses) == len(_NO_PARAM_METHODS)
    for i, resp in enumerate(responses):
        assert resp.ok, f"{_NO_PARAM_METHODS[i]} failed in batch: {resp.error}"
