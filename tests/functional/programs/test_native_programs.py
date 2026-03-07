"""Functional tests: Native program accounts existence and properties.

Verifies that all native/builtin programs karstflow implements are
accessible, have correct ownership, and are marked as executable.
"""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

# ── All native programs implemented by karstflow ──────────────────────

NATIVE_PROGRAMS = [
    ("system_program", "11111111111111111111111111111111"),
    ("vote_program", "Vote111111111111111111111111111111111111111"),
    ("stake_program", "Stake11111111111111111111111111111111111111"),
    ("config_program", "Config1111111111111111111111111111111111111"),
    ("bpf_loader_v2", "BPFLoader2111111111111111111111111111111111"),
    ("bpf_loader_upgradeable", "BPFLoaderUpgradeab1e11111111111111111111111"),
    ("compute_budget", "ComputeBudget111111111111111111111111111"),
    ("address_lookup_table", "AddressLookupTab1e1111111111111111111111111"),
    ("feature_program", "Feature111111111111111111111111111111111111"),
]

NATIVE_PROGRAM_IDS = [name for name, _ in NATIVE_PROGRAMS]

SPL_PROGRAMS = [
    ("token_program", "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"),
    ("memo_program_v2", "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"),
]

SPL_PROGRAM_IDS = [name for name, _ in SPL_PROGRAMS]

PRECOMPILE_PROGRAMS = [
    ("ed25519", "Ed25519SigVerify111111111111111111111111111"),
    ("secp256k1", "KeccakSecp256k11111111111111111111111111111"),
]

PRECOMPILE_PROGRAM_IDS = [name for name, _ in PRECOMPILE_PROGRAMS]


# ── Native program existence tests ───────────────────────────────────


@pytest.mark.parametrize(("name", "pubkey"), NATIVE_PROGRAMS, ids=NATIVE_PROGRAM_IDS)
async def test_native_program_exists(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """Native program account exists on chain."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None, f"Native program {name} ({pubkey}) not found"


@pytest.mark.parametrize(("name", "pubkey"), NATIVE_PROGRAMS, ids=NATIVE_PROGRAM_IDS)
async def test_native_program_is_executable(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """Native program is marked as executable."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert result.value.executable, f"{name} should be executable"


@pytest.mark.parametrize(("name", "pubkey"), NATIVE_PROGRAMS, ids=NATIVE_PROGRAM_IDS)
async def test_native_program_owned_by_native_loader(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """Native program is owned by NativeLoader."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    owner = str(result.value.owner)
    # Native programs are owned by NativeLoader1111... or BPFLoader for SPL
    assert owner in (
        "NativeLoader1111111111111111111111111111111",
        "BPFLoader2111111111111111111111111111111111",
        "BPFLoaderUpgradeab1e11111111111111111111111",
    ), f"{name} unexpected owner: {owner}"


# ── SPL program tests ────────────────────────────────────────────────


@pytest.mark.parametrize(("name", "pubkey"), SPL_PROGRAMS, ids=SPL_PROGRAM_IDS)
async def test_spl_program_exists(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """SPL program account exists on chain."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None, f"SPL program {name} ({pubkey}) not found"


@pytest.mark.parametrize(("name", "pubkey"), SPL_PROGRAMS, ids=SPL_PROGRAM_IDS)
async def test_spl_program_is_executable(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """SPL program is executable."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None
    assert result.value.executable, f"{name} should be executable"


# ── Precompile program tests ────────────────────────────────────────


@pytest.mark.parametrize(("name", "pubkey"), PRECOMPILE_PROGRAMS, ids=PRECOMPILE_PROGRAM_IDS)
async def test_precompile_exists(
    solana_client: AsyncClient,
    name: str,
    pubkey: str,
) -> None:
    """Precompile program account exists on chain."""
    pk = Pubkey.from_string(pubkey)
    result = await solana_client.get_account_info(pk)
    assert result.value is not None, f"Precompile {name} ({pubkey}) not found"
