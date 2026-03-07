"""Functional tests: RPC error responses and error codes.

Verifies that the validator returns correct JSON-RPC error responses
for various invalid request scenarios.
"""

from __future__ import annotations

import pytest

from karstflow_tests.rpc import RpcClient
from karstflow_tests.types import RpcCallError


async def test_invalid_method_returns_error(rpc_client: RpcClient) -> None:
    """Unknown method returns JSON-RPC error."""
    resp = await rpc_client.request_raw("totallyBogusMethod")
    assert not resp.ok
    assert resp.error is not None
    assert resp.error.code == -32601  # Method not found


async def test_invalid_params_type(rpc_client: RpcClient) -> None:
    """Wrong param type returns error."""
    resp = await rpc_client.request_raw("getBalance", ["not-a-valid-pubkey"])
    assert not resp.ok
    assert resp.error is not None


async def test_missing_required_params(rpc_client: RpcClient) -> None:
    """Missing required params returns error."""
    resp = await rpc_client.request_raw("getBalance")
    assert not resp.ok
    assert resp.error is not None


async def test_invalid_commitment_value(rpc_client: RpcClient) -> None:
    """Invalid commitment value returns error or is ignored."""
    resp = await rpc_client.request_raw("getSlot", [{"commitment": "bogus_commitment"}])
    # Implementations may either error or ignore invalid commitment
    # We just verify it doesn't crash
    assert resp is not None


async def test_negative_slot_returns_error(rpc_client: RpcClient) -> None:
    """Negative slot number in getBlock returns error."""
    resp = await rpc_client.request_raw("getBlock", [-1])
    assert not resp.ok
    assert resp.error is not None


async def test_future_slot_returns_null(rpc_client: RpcClient) -> None:
    """Far future slot in getBlock returns null."""
    resp = await rpc_client.request_raw("getBlock", [999_999_999])
    # Either error or null result
    if resp.ok:
        assert resp.result is None
    else:
        assert resp.error is not None


async def test_error_has_code_and_message(rpc_client: RpcClient) -> None:
    """RPC errors have both code and message fields."""
    resp = await rpc_client.request_raw("nonExistentMethod")
    assert resp.error is not None
    assert isinstance(resp.error.code, int)
    assert isinstance(resp.error.message, str)
    assert len(resp.error.message) > 0


async def test_unwrap_raises_on_error(rpc_client: RpcClient) -> None:
    """RpcResponse.unwrap() raises RpcCallError on error response."""
    resp = await rpc_client.request_raw("nonExistentMethod")
    with pytest.raises(RpcCallError) as exc_info:
        resp.unwrap()
    assert exc_info.value.code == -32601


async def test_batch_with_mixed_valid_invalid(rpc_client: RpcClient) -> None:
    """Batch with both valid and invalid requests returns mixed results."""
    responses = await rpc_client.batch(
        [
            ("getSlot", None),
            ("nonExistentMethod", None),
            ("getHealth", None),
        ]
    )
    assert len(responses) == 3
    assert responses[0].ok  # getSlot
    assert not responses[1].ok  # nonExistentMethod
    assert responses[2].ok  # getHealth


async def test_empty_method_name(rpc_client: RpcClient) -> None:
    """Empty method name returns error."""
    resp = await rpc_client.request_raw("")
    assert not resp.ok


async def test_getblock_skipped_slot(rpc_client: RpcClient) -> None:
    """getBlock for slot 0 (likely skipped or genesis)."""
    resp = await rpc_client.request_raw("getBlock", [0, {"maxSupportedTransactionVersion": 0}])
    # Slot 0 may be skipped — either null result or error is fine
    assert resp is not None
