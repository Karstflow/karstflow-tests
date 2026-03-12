"""Functional tests: getProgramAccounts."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import STAKE_PROGRAM, SYSTEM_PROGRAM, VOTE_PROGRAM


async def test_get_program_accounts_system(raw_rpc: RpcClient) -> None:
    """getProgramAccounts for system program returns accounts."""
    # System program owns many accounts; limit via dataSize filter
    result = await raw_rpc.get_program_accounts(
        SYSTEM_PROGRAM,
        filters=[{"dataSize": 0}],
    )
    assert isinstance(result, list)


async def test_get_program_accounts_vote(raw_rpc: RpcClient) -> None:
    """getProgramAccounts for vote program returns list (may be empty in dev mode)."""
    result = await raw_rpc.get_program_accounts(VOTE_PROGRAM)
    assert isinstance(result, list)
    # In dev mode without program account indexing, this may return empty.
    # Validate structure when results are present.
    for entry in result:
        assert "pubkey" in entry
        assert "account" in entry
        assert entry["account"]["owner"] == VOTE_PROGRAM


async def test_get_program_accounts_with_data_size_filter(raw_rpc: RpcClient) -> None:
    """getProgramAccounts with dataSize filter narrows results."""
    # Stake accounts are 200 bytes
    result = await raw_rpc.get_program_accounts(
        STAKE_PROGRAM,
        filters=[{"dataSize": 200}],
    )
    assert isinstance(result, list)
    for entry in result:
        assert entry["account"]["owner"] == STAKE_PROGRAM


async def test_get_program_accounts_empty_for_nonexistent(raw_rpc: RpcClient) -> None:
    """getProgramAccounts for non-program pubkey returns empty list."""
    from solders.keypair import Keypair

    random_key = str(Keypair().pubkey())
    resp = await raw_rpc.request_raw("getProgramAccounts", [random_key])
    # Either empty list or error (invalid program)
    if resp.ok:
        assert resp.result == []
    else:
        assert resp.error is not None
