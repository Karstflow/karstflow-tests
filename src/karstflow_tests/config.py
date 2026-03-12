"""Centralized test configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class Commitment(Enum):
    """Solana commitment levels."""

    PROCESSED = "processed"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy for RPC requests."""

    max_retries: int = 3
    backoff_base: float = 0.5
    backoff_max: float = 10.0
    retryable_codes: tuple[int, ...] = (-32005, -32016)  # node behind, slot skipped


@dataclass(frozen=True)
class TestConfig:
    """Top-level test configuration resolved from environment."""

    rpc_url: str = field(
        default_factory=lambda: os.environ.get("KARSTFLOW_RPC_URL", "http://localhost:8899")
    )
    ws_url: str = field(
        default_factory=lambda: os.environ.get("KARSTFLOW_WS_URL", "ws://localhost:8899")
    )
    default_commitment: Commitment = Commitment.CONFIRMED
    request_timeout: float = 30.0
    ws_recv_timeout: float = 10.0
    airdrop_lamports: int = 10_000_000_000
    confirmation_timeout: float = 30.0
    health_timeout: float = 30.0
    retry: RetryPolicy = field(default_factory=RetryPolicy)


def load_config() -> TestConfig:
    """Load test configuration from environment."""
    return TestConfig()
