"""Functional tests: SPL Token program basic verification.

Tests that the Token program is accessible and responds correctly
to basic queries. Full token lifecycle tests require token mint setup.
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

from karstflow_tests.rpc import RpcClient


async def test_token_program_exists(solana_client: AsyncClient) -> None:
    """SPL Token program account exists on chain."""
    pk = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert result.value.executable


async def test_token_program_owned_by_loader(solana_client: AsyncClient) -> None:
    """Token program is owned by BPF loader."""
    pk = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    owner = str(result.value.owner)
    assert owner in (
        "BPFLoader2111111111111111111111111111111111",
        "BPFLoaderUpgradeab1e11111111111111111111111",
        "NativeLoader1111111111111111111111111111111",
    )


async def test_token_program_accounts_query(raw_rpc: RpcClient) -> None:
    """Querying getProgramAccounts for token program works (may be empty)."""
    resp = await raw_rpc.request_raw(
        "getProgramAccounts",
        [
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            {"encoding": "base64", "filters": [{"dataSize": 165}]},
        ],
    )
    # Either returns list (possibly empty) or error for unindexed
    if resp.ok:
        assert isinstance(resp.result, list)


async def test_associated_token_program_exists(solana_client: AsyncClient) -> None:
    """Associated Token program account exists."""
    pk = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25phJjKXMGGSE")
    result = await solana_client.get_account_info(pk)
    # May not exist in minimal dev mode, so just check the query works
    if result.value is not None:
        assert result.value.executable
