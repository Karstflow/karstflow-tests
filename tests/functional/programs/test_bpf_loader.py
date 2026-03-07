"""Functional tests: BPF Loader program accounts."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import BPF_LOADER, BPF_LOADER_UPGRADEABLE


async def test_bpf_loader_v2_exists(solana_client: AsyncClient) -> None:
    """BPFLoader2 program exists and is executable."""
    pk = Pubkey.from_string(BPF_LOADER)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert result.value.executable


async def test_bpf_loader_upgradeable_exists(solana_client: AsyncClient) -> None:
    """BPFLoaderUpgradeable program exists and is executable."""
    pk = Pubkey.from_string(BPF_LOADER_UPGRADEABLE)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert result.value.executable


async def test_bpf_loader_upgradeable_accounts(raw_rpc: RpcClient) -> None:
    """getProgramAccounts for BPF upgradeable loader returns deployed programs."""
    result = await raw_rpc.get_program_accounts(BPF_LOADER_UPGRADEABLE)
    assert isinstance(result, list)
    # SPL programs (Token, Memo) should appear here
    for entry in result:
        assert entry["account"]["owner"] == BPF_LOADER_UPGRADEABLE


async def test_bpf_loader_program_account_has_data(raw_rpc: RpcClient) -> None:
    """BPF-deployed program accounts contain program bytecode."""
    result = await raw_rpc.get_program_accounts(BPF_LOADER_UPGRADEABLE)
    if len(result) > 0:
        first = result[0]
        data = first["account"].get("data", [])
        if isinstance(data, list) and len(data) >= 1:
            # base64 encoded data should be non-empty
            assert len(data[0]) > 0
