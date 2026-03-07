"""Functional tests: getLargestAccounts."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_largest_accounts_returns_list(raw_rpc: RpcClient) -> None:
    """getLargestAccounts returns a list of accounts."""
    result = await raw_rpc.get_largest_accounts()
    assert isinstance(result, dict)
    assert "value" in result
    accounts = result["value"]
    assert isinstance(accounts, list)
    assert len(accounts) > 0


async def test_largest_accounts_have_required_fields(raw_rpc: RpcClient) -> None:
    """Each account entry has address and lamports."""
    result = await raw_rpc.get_largest_accounts()
    for account in result["value"][:5]:
        assert "address" in account
        assert "lamports" in account
        assert isinstance(account["lamports"], int)
        assert account["lamports"] > 0


async def test_largest_accounts_sorted_descending(raw_rpc: RpcClient) -> None:
    """Accounts should be sorted by balance descending."""
    result = await raw_rpc.get_largest_accounts()
    accounts = result["value"]
    if len(accounts) >= 2:
        for i in range(len(accounts) - 1):
            assert accounts[i]["lamports"] >= accounts[i + 1]["lamports"]
