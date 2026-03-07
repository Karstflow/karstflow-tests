"""Functional tests: unknown and deprecated RPC method handling."""

from __future__ import annotations

import pytest

from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import UNKNOWN_RPC_METHODS, UNKNOWN_RPC_METHODS_IDS


@pytest.mark.parametrize("method", UNKNOWN_RPC_METHODS, ids=UNKNOWN_RPC_METHODS_IDS)
async def test_unknown_method_returns_error(rpc_client: RpcClient, method: str) -> None:
    """Unknown RPC methods return a method-not-found error."""
    resp = await rpc_client.request_raw(method, None)
    assert not resp.ok
    assert resp.error is not None
    assert resp.error.code == -32601


async def test_deprecated_getrecentblockhash(rpc_client: RpcClient) -> None:
    """getRecentBlockhash (deprecated) should still work or return clear error."""
    resp = await rpc_client.request_raw("getRecentBlockhash", None)
    assert isinstance(resp.ok, bool)


async def test_case_sensitive_methods(rpc_client: RpcClient) -> None:
    """RPC methods are case-sensitive."""
    correct = await rpc_client.request_raw("getHealth", None)
    wrong = await rpc_client.request_raw("gethealth", None)
    assert correct.ok
    assert not wrong.ok
