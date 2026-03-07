"""Functional tests: invalid parameter handling (negative cases)."""

from __future__ import annotations

import pytest

from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import INVALID_PUBKEYS, INVALID_PUBKEYS_IDS


async def test_get_balance_invalid_pubkey(rpc_client: RpcClient) -> None:
    """getBalance with invalid pubkey returns error."""
    resp = await rpc_client.request_raw("getBalance", ["not-a-valid-pubkey"])
    assert not resp.ok
    assert resp.error is not None
    assert resp.error.code == -32602  # Invalid params


async def test_get_account_info_invalid_pubkey(rpc_client: RpcClient) -> None:
    """getAccountInfo with invalid pubkey returns error."""
    resp = await rpc_client.request_raw("getAccountInfo", ["ZZZZ"])
    assert not resp.ok


async def test_get_block_negative_slot(rpc_client: RpcClient) -> None:
    """getBlock with negative slot returns error."""
    resp = await rpc_client.request_raw("getBlock", [-1])
    assert not resp.ok


async def test_get_block_future_slot(rpc_client: RpcClient) -> None:
    """getBlock with far-future slot returns error or null."""
    resp = await rpc_client.request_raw("getBlock", [999_999_999])
    assert not resp.ok or resp.result is None


async def test_send_transaction_empty(rpc_client: RpcClient) -> None:
    """sendTransaction with empty string returns error."""
    resp = await rpc_client.request_raw("sendTransaction", [""])
    assert not resp.ok


async def test_send_transaction_garbage(rpc_client: RpcClient) -> None:
    """sendTransaction with garbage data returns error."""
    resp = await rpc_client.request_raw("sendTransaction", ["not-a-transaction-at-all"])
    assert not resp.ok


@pytest.mark.parametrize("invalid_key", INVALID_PUBKEYS, ids=INVALID_PUBKEYS_IDS)
async def test_get_balance_various_invalid_keys(rpc_client: RpcClient, invalid_key: str) -> None:
    """getBalance rejects various invalid pubkey formats."""
    resp = await rpc_client.request_raw("getBalance", [invalid_key])
    assert not resp.ok


async def test_missing_params(rpc_client: RpcClient) -> None:
    """RPC methods requiring params return error when params are missing."""
    resp = await rpc_client.request_raw("getBalance", None)
    assert not resp.ok


async def test_wrong_param_type(rpc_client: RpcClient) -> None:
    """Passing wrong type (number instead of string) returns error."""
    resp = await rpc_client.request_raw("getBalance", [12345])
    assert not resp.ok


async def test_extra_params_ignored_or_error(rpc_client: RpcClient) -> None:
    """Extra params are either ignored or cause error (not crash)."""
    resp = await rpc_client.request_raw("getHealth", ["extra", "params", 123])
    assert isinstance(resp.ok, bool)
