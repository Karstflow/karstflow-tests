"""Functional tests: Vote program accounts and data inspection."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import VOTE_PROGRAM


async def test_vote_accounts_current_nonempty(raw_rpc: RpcClient) -> None:
    """getVoteAccounts returns at least one current validator."""
    result = await raw_rpc.get_vote_accounts()
    assert "current" in result
    assert len(result["current"]) >= 1


async def test_vote_accounts_fields(raw_rpc: RpcClient) -> None:
    """Current vote accounts have required fields."""
    result = await raw_rpc.get_vote_accounts()
    for va in result["current"]:
        assert "votePubkey" in va
        assert "nodePubkey" in va
        assert "activatedStake" in va
        assert "commission" in va
        assert "epochCredits" in va
        assert "lastVote" in va
        assert isinstance(va["commission"], int)
        assert 0 <= va["commission"] <= 100


async def test_vote_accounts_commission_range(raw_rpc: RpcClient) -> None:
    """Vote account commission is within valid range [0, 100]."""
    result = await raw_rpc.get_vote_accounts()
    for va in result["current"]:
        assert 0 <= va["commission"] <= 100


async def test_vote_accounts_activated_stake(raw_rpc: RpcClient) -> None:
    """Current validators have positive activated stake."""
    result = await raw_rpc.get_vote_accounts()
    for va in result["current"]:
        assert va["activatedStake"] > 0


async def test_vote_accounts_epoch_credits(raw_rpc: RpcClient) -> None:
    """Vote account epoch credits is a non-empty list of tuples."""
    result = await raw_rpc.get_vote_accounts()
    for va in result["current"]:
        credits = va["epochCredits"]
        assert isinstance(credits, list)
        if len(credits) > 0:
            # Each entry: [epoch, credits, prevCredits]
            entry = credits[-1]
            assert isinstance(entry, list)
            assert len(entry) == 3


async def test_vote_program_accounts_exist(raw_rpc: RpcClient) -> None:
    """getProgramAccounts for Vote program returns vote accounts."""
    result = await raw_rpc.get_program_accounts(VOTE_PROGRAM)
    assert isinstance(result, list)
    assert len(result) >= 1
    for entry in result:
        assert entry["account"]["owner"] == VOTE_PROGRAM


async def test_vote_account_data_size(raw_rpc: RpcClient) -> None:
    """Vote account data is a meaningful size."""
    result = await raw_rpc.get_program_accounts(VOTE_PROGRAM)
    for entry in result[:3]:
        account = entry["account"]
        data = account.get("data", [])
        # Vote accounts are variable-size but substantial
        if isinstance(data, list) and len(data) >= 1:
            assert len(data[0]) > 10  # base64 encoded data exists


async def test_vote_accounts_node_pubkey_in_cluster(raw_rpc: RpcClient) -> None:
    """Vote account nodePubkey matches a cluster node identity."""
    vote_result = await raw_rpc.get_vote_accounts()
    cluster_nodes = await raw_rpc.get_cluster_nodes()

    cluster_pubkeys = {node["pubkey"] for node in cluster_nodes}
    for va in vote_result["current"]:
        assert va["nodePubkey"] in cluster_pubkeys
