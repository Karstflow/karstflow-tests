"""RPC method coverage tracking for test runs.

Tracks which Solana JSON-RPC methods have been called during tests,
enabling coverage reports for API method completeness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Complete list of Solana JSON-RPC methods
ALL_RPC_METHODS: frozenset[str] = frozenset(
    {
        # Account
        "getAccountInfo",
        "getBalance",
        "getLargestAccounts",
        "getMultipleAccounts",
        "getProgramAccounts",
        "getTokenAccountBalance",
        "getTokenAccountsByDelegate",
        "getTokenAccountsByOwner",
        "getTokenLargestAccounts",
        "getTokenSupply",
        # Block
        "getBlock",
        "getBlockCommitment",
        "getBlockHeight",
        "getBlockProduction",
        "getBlockTime",
        "getBlocks",
        "getBlocksWithLimit",
        "getFirstAvailableBlock",
        # Cluster
        "getClusterNodes",
        "getEpochInfo",
        "getEpochSchedule",
        "getGenesisHash",
        "getHealth",
        "getHighestSnapshotSlot",
        "getIdentity",
        "getInflationGovernor",
        "getInflationRate",
        "getInflationReward",
        "getLeaderSchedule",
        "getMaxRetransmitSlot",
        "getMaxShredInsertSlot",
        "getRecentPerformanceSamples",
        "getSlot",
        "getSlotLeader",
        "getSlotLeaders",
        "getSupply",
        "getStakeMinimumDelegation",
        "getVersion",
        "getVoteAccounts",
        "minimumLedgerSlot",
        # Transaction
        "getFeeForMessage",
        "getLatestBlockhash",
        "getMinimumBalanceForRentExemption",
        "getRecentPrioritizationFees",
        "getSignatureStatuses",
        "getSignaturesForAddress",
        "getTransaction",
        "getTransactionCount",
        "isBlockhashValid",
        "requestAirdrop",
        "sendTransaction",
        "simulateTransaction",
        # Deprecated but still used
        "getFees",
        "getStakeActivation",
    }
)


@dataclass
class MethodCoverage:
    """Tracks which RPC methods have been called."""

    called: set[str] = field(default_factory=set)

    def record(self, method: str) -> None:
        """Record a single RPC method call."""
        self.called.add(method)

    def record_many(self, methods: list[str]) -> None:
        """Record multiple RPC method calls."""
        self.called.update(methods)

    @property
    def covered(self) -> frozenset[str]:
        """Return the set of known methods that have been called."""
        return frozenset(self.called & ALL_RPC_METHODS)

    @property
    def uncovered(self) -> frozenset[str]:
        """Return the set of known methods that have not been called."""
        return ALL_RPC_METHODS - self.called

    @property
    def coverage_pct(self) -> float:
        """Return coverage percentage (0.0 - 100.0)."""
        if not ALL_RPC_METHODS:
            return 100.0
        return len(self.covered) / len(ALL_RPC_METHODS) * 100

    def report(self) -> str:
        """Generate a human-readable coverage report."""
        lines = [
            f"RPC Method Coverage: {self.coverage_pct:.1f}%"
            f" ({len(self.covered)}/{len(ALL_RPC_METHODS)})",
            "",
            "Covered:",
        ]
        for m in sorted(self.covered):
            lines.append(f"  + {m}")
        if self.uncovered:
            lines.append("")
            lines.append("Not covered:")
            for m in sorted(self.uncovered):
                lines.append(f"  - {m}")
        return "\n".join(lines)
