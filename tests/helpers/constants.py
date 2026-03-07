"""Shared test constants and parametrization data.

Reusable data sets for parametrized tests across all test groups.
"""

from __future__ import annotations

# ── Well-known program addresses ─────────────────────────────────────

SYSTEM_PROGRAM = "11111111111111111111111111111111"
VOTE_PROGRAM = "Vote111111111111111111111111111111111111111"
STAKE_PROGRAM = "Stake11111111111111111111111111111111111111"
CONFIG_PROGRAM = "Config1111111111111111111111111111111111111"
BPF_LOADER = "BPFLoader2111111111111111111111111111111111"
BPF_LOADER_UPGRADEABLE = "BPFLoaderUpgradeab1e11111111111111111111111"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
MEMO_PROGRAM = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"

NATIVE_PROGRAMS: list[tuple[str, str]] = [
    ("system_program", SYSTEM_PROGRAM),
    ("vote_program", VOTE_PROGRAM),
    ("stake_program", STAKE_PROGRAM),
    ("config_program", CONFIG_PROGRAM),
    ("bpf_loader", BPF_LOADER),
    ("bpf_loader_upgradeable", BPF_LOADER_UPGRADEABLE),
]

# ── Common airdrop amounts ───────────────────────────────────────────

AIRDROP_1_SOL = 1_000_000_000
AIRDROP_5_SOL = 5_000_000_000
AIRDROP_10_SOL = 10_000_000_000

TRANSFER_AMOUNTS = [1, 1_000, 1_000_000, 100_000_000, 1_000_000_000]
TRANSFER_AMOUNTS_IDS = ["1_lamport", "1K", "1M", "100M", "1_SOL"]

# ── Rent exemption data sizes ────────────────────────────────────────

RENT_DATA_SIZES = [0, 32, 128, 1024, 10240, 165]
RENT_DATA_SIZES_IDS = ["0B", "32B", "128B", "1KB", "10KB", "token_account"]

# ── Invalid pubkey strings ───────────────────────────────────────────

INVALID_PUBKEYS = ["", "not-a-key", "11111", "0" * 100]
INVALID_PUBKEYS_IDS = ["empty", "text", "short", "long_zeros"]

# ── RPC method names ────────────────────────────────────────────────

UNKNOWN_RPC_METHODS = [
    "nonExistentMethod",
    "getNothing",
    "foo",
    "bar.baz",
    "",
]
UNKNOWN_RPC_METHODS_IDS = ["camelCase", "getPrefix", "short", "dotted", "empty"]
