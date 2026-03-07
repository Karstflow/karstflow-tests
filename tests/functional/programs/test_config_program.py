"""Functional tests: Config program account inspection."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import CONFIG_PROGRAM


async def test_config_program_exists(solana_client: AsyncClient) -> None:
    """Config program is deployed and executable."""
    pk = Pubkey.from_string(CONFIG_PROGRAM)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert result.value.executable


async def test_config_program_accounts(raw_rpc: RpcClient) -> None:
    """getProgramAccounts for Config program returns accounts (if any)."""
    result = await raw_rpc.get_program_accounts(CONFIG_PROGRAM)
    assert isinstance(result, list)
    # Config accounts may exist in dev for validator config
    for entry in result:
        assert entry["account"]["owner"] == CONFIG_PROGRAM
