"""Functional tests: Address Lookup Table program."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey


async def test_address_lookup_table_program_exists(solana_client: AsyncClient) -> None:
    """Address Lookup Table program account exists."""
    pk = Pubkey.from_string("AddressLookupTab1e1111111111111111111111111")
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert result.value.executable


async def test_address_lookup_table_program_properties(solana_client: AsyncClient) -> None:
    """Address Lookup Table program has correct properties."""
    pk = Pubkey.from_string("AddressLookupTab1e1111111111111111111111111")
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    # Should be owned by native loader
    owner = str(result.value.owner)
    assert owner in (
        "NativeLoader1111111111111111111111111111111",
        "BPFLoaderUpgradeab1e11111111111111111111111",
    )
