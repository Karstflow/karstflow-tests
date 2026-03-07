"""Functional tests: getVoteAccounts."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_vote_accounts_current(rpc_client: RpcClient) -> None:
    """getVoteAccounts returns current vote accounts."""
    result = await rpc_client.get_vote_accounts()
    assert "current" in result
    assert "delinquent" in result
    assert isinstance(result["current"], list)


async def test_vote_account_fields(rpc_client: RpcClient) -> None:
    """Vote account entries have expected fields."""
    result = await rpc_client.get_vote_accounts()
    if result["current"]:
        account = result["current"][0]
        assert "votePubkey" in account
        assert "nodePubkey" in account
        assert "activatedStake" in account
        assert "lastVote" in account
        assert "commission" in account


async def test_at_least_one_voter(rpc_client: RpcClient) -> None:
    """In dev mode, there should be at least one active voter."""
    result = await rpc_client.get_vote_accounts()
    total = len(result["current"]) + len(result["delinquent"])
    assert total >= 1
