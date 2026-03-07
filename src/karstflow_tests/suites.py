"""Named test suite registry for organizing test runs by purpose.

Provides a declarative way to define collections of test paths/markers
that correspond to specific testing objectives.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TestSuite:
    """A named collection of tests with metadata."""

    name: str
    description: str
    paths: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    timeout: int = 60
    requires_node: bool = True
    requires_cluster: bool = False
    extra_args: list[str] = field(default_factory=list)

    def pytest_args(self) -> list[str]:
        """Generate pytest command-line arguments for this suite."""
        args: list[str] = []
        args.extend(self.paths)
        if self.markers:
            args.extend(["-m", " or ".join(self.markers)])
        if self.keywords:
            args.extend(["-k", " or ".join(self.keywords)])
        args.extend(["--timeout", str(self.timeout)])
        args.extend(self.extra_args)
        return args

    def pytest_cmd(self, *, verbose: bool = True) -> str:
        """Generate the full pytest command string."""
        args = self.pytest_args()
        if verbose:
            args.append("-v")
        return "uv run pytest " + " ".join(args)


# ── Built-in suites ─────────────────────────────────────────────────────

SUITES: dict[str, TestSuite] = {}


def register(suite: TestSuite) -> TestSuite:
    """Register a test suite in the global registry."""
    SUITES[suite.name] = suite
    return suite


def get_suite(name: str) -> TestSuite:
    """Look up a suite by name. Raises KeyError if not found."""
    return SUITES[name]


def list_suites() -> list[TestSuite]:
    """Return all registered suites sorted by name."""
    return sorted(SUITES.values(), key=lambda s: s.name)


# ── Smoke ────────────────────────────────────────────────────────────────

register(
    TestSuite(
        name="smoke",
        description="Quick sanity: health, version, genesis hash (<30s)",
        paths=["tests/smoke"],
        markers=["smoke"],
        timeout=30,
    )
)

# ── Functional groups ────────────────────────────────────────────────────

register(
    TestSuite(
        name="accounts",
        description="Account RPC methods: balance, info, encoding, airdrop",
        paths=["tests/functional/accounts"],
        timeout=60,
    )
)

register(
    TestSuite(
        name="transactions",
        description="Transaction lifecycle: send, simulate, confirm, query",
        paths=["tests/functional/transactions"],
        timeout=90,
    )
)

register(
    TestSuite(
        name="blocks",
        description="Block/slot/epoch queries and commitment levels",
        paths=["tests/functional/blocks"],
        timeout=60,
    )
)

register(
    TestSuite(
        name="network",
        description="Network info: supply, inflation, rent, fees",
        paths=["tests/functional/network"],
        timeout=60,
    )
)

register(
    TestSuite(
        name="cluster-info",
        description="Cluster queries: nodes, leader schedule, vote accounts",
        paths=["tests/functional/cluster_info"],
        timeout=60,
    )
)

register(
    TestSuite(
        name="errors",
        description="Error handling: invalid params, unknown methods, edge cases",
        paths=["tests/functional/errors"],
        timeout=60,
    )
)

register(
    TestSuite(
        name="programs",
        description="Native programs: system, token, memo, compute budget, sysvars",
        paths=["tests/functional/programs"],
        markers=["programs"],
        timeout=90,
    )
)

# ── Cross-cutting suites ────────────────────────────────────────────────

register(
    TestSuite(
        name="functional",
        description="All single-node functional tests",
        paths=["tests/functional"],
        markers=["functional"],
        timeout=60,
    )
)

register(
    TestSuite(
        name="websocket",
        description="WebSocket subscription tests",
        paths=["tests/websocket"],
        markers=["websocket"],
        timeout=60,
    )
)

register(
    TestSuite(
        name="integration",
        description="Multi-node cluster tests (requires 3-node cluster)",
        paths=["tests/integration"],
        markers=["integration"],
        timeout=120,
        requires_cluster=True,
    )
)

register(
    TestSuite(
        name="load",
        description="Performance and load tests",
        paths=["tests/load"],
        markers=["load"],
        timeout=300,
    )
)

# ── Purpose-specific suites ─────────────────────────────────────────────

register(
    TestSuite(
        name="quick",
        description="Fast feedback: smoke + basic functional (< 2 min)",
        paths=["tests/smoke", "tests/functional/accounts", "tests/functional/blocks"],
        timeout=30,
    )
)

register(
    TestSuite(
        name="rpc-compat",
        description="RPC compatibility: all methods that test Solana RPC spec compliance",
        paths=["tests/functional"],
        timeout=60,
        extra_args=["--rpc-coverage"],
    )
)

register(
    TestSuite(
        name="token-lifecycle",
        description="Full token lifecycle: create mint, accounts, mint, transfer, burn, close",
        paths=[
            "tests/functional/programs/test_token_program.py",
            "tests/functional/programs/test_token_lifecycle.py",
            "tests/functional/programs/test_token_advanced.py",
            "tests/functional/accounts/test_token_queries.py",
        ],
        timeout=90,
    )
)

register(
    TestSuite(
        name="tx-lifecycle",
        description="Transaction lifecycle: build, send, confirm, query, simulate",
        paths=[
            "tests/functional/transactions/test_send_transaction.py",
            "tests/functional/transactions/test_transfer.py",
            "tests/functional/transactions/test_get_transaction.py",
            "tests/functional/transactions/test_transaction_lifecycle.py",
            "tests/functional/transactions/test_commitment_lifecycle.py",
        ],
        timeout=90,
    )
)

register(
    TestSuite(
        name="pre-merge",
        description="Pre-merge gate: smoke + functional + websocket (no cluster)",
        paths=["tests/smoke", "tests/functional", "tests/websocket"],
        timeout=60,
    )
)

register(
    TestSuite(
        name="full",
        description="Full test suite: all tests including integration (requires cluster)",
        paths=["tests/smoke", "tests/functional", "tests/websocket", "tests/integration"],
        timeout=120,
        requires_cluster=True,
        extra_args=["--rpc-coverage"],
    )
)


def suite_help() -> str:
    """Generate formatted help text listing all suites."""
    lines = ["Available test suites:", ""]
    max_name = max(len(s.name) for s in SUITES.values())
    for suite in list_suites():
        cluster = " [cluster]" if suite.requires_cluster else ""
        lines.append(f"  {suite.name:<{max_name + 2}} {suite.description}{cluster}")
    return "\n".join(lines)
