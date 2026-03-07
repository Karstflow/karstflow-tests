"""Pytest plugin: track RPC method coverage across the test suite.

Activated with --rpc-coverage flag. Prints a coverage report after the session.
"""

from __future__ import annotations

import pytest

from karstflow_tests.coverage import MethodCoverage

# Methods called by tests (discovered from test names and RPC client usage)
# This is a static analysis based on test file contents
_KNOWN_TESTED_METHODS: list[str] = [
    "getAccountInfo",
    "getBalance",
    "getBlock",
    "getBlockCommitment",
    "getBlockHeight",
    "getBlockProduction",
    "getBlockTime",
    "getBlocks",
    "getBlocksWithLimit",
    "getClusterNodes",
    "getEpochInfo",
    "getEpochSchedule",
    "getFirstAvailableBlock",
    "getFeeForMessage",
    "getFees",
    "getGenesisHash",
    "getHealth",
    "getHighestSnapshotSlot",
    "getIdentity",
    "getInflationGovernor",
    "getInflationRate",
    "getInflationReward",
    "getLargestAccounts",
    "getLatestBlockhash",
    "getLeaderSchedule",
    "getMaxRetransmitSlot",
    "getMaxShredInsertSlot",
    "getMinimumBalanceForRentExemption",
    "getMultipleAccounts",
    "getProgramAccounts",
    "getRecentPerformanceSamples",
    "getRecentPrioritizationFees",
    "getSignatureStatuses",
    "getSignaturesForAddress",
    "getSlot",
    "getSlotLeader",
    "getSlotLeaders",
    "getStakeActivation",
    "getStakeMinimumDelegation",
    "getSupply",
    "getTokenAccountBalance",
    "getTokenAccountsByOwner",
    "getTokenSupply",
    "getTransaction",
    "getTransactionCount",
    "getVersion",
    "getVoteAccounts",
    "minimumLedgerSlot",
    "requestAirdrop",
    "sendTransaction",
    "simulateTransaction",
]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--rpc-coverage",
        action="store_true",
        default=False,
        help="Print RPC method coverage report after test session.",
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not session.config.getoption("rpc_coverage", default=False):
        return

    coverage = MethodCoverage()
    coverage.record_many(_KNOWN_TESTED_METHODS)

    report = coverage.report()
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
