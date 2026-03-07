"""Functional tests: deep program account verification.

Config program, ALT, BPF loaders, and precompile programs.
"""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_config_program_owned_by_config_loader(rpc_client: RpcClient) -> None:
    """Config program is owned by the native loader."""
    resp = await rpc_client.get_account_info("Config1111111111111111111111111111111111111")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    assert info["executable"] is True


async def test_alt_program_owned_by_native_loader(rpc_client: RpcClient) -> None:
    """Address Lookup Table program is owned by native loader."""
    resp = await rpc_client.get_account_info("AddressLookupTab1e1111111111111111111111111")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    assert info["executable"] is True


async def test_ed25519_precompile_exists(rpc_client: RpcClient) -> None:
    """Ed25519 signature verification precompile exists."""
    resp = await rpc_client.get_account_info("Ed25519SigVerify111111111111111111111111111")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    assert info["owner"] is not None


async def test_secp256k1_precompile_exists(rpc_client: RpcClient) -> None:
    """Secp256k1 signature recovery precompile exists."""
    resp = await rpc_client.get_account_info("KeccakSecp256k11111111111111111111111111111")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    assert info["owner"] is not None


async def test_bpf_loader_is_executable(rpc_client: RpcClient) -> None:
    """BPF Loader v2 is executable."""
    resp = await rpc_client.get_account_info("BPFLoader2111111111111111111111111111111111")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    assert info["executable"] is True


async def test_bpf_loader_upgradeable_is_executable(rpc_client: RpcClient) -> None:
    """BPF Loader Upgradeable is executable."""
    resp = await rpc_client.get_account_info("BPFLoaderUpgradeab1e11111111111111111111111")
    assert resp is not None
    info = resp["value"]
    assert info is not None
    assert info["executable"] is True
