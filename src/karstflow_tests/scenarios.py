"""Multi-step test scenario orchestrator.

Provides a structured way to define test scenarios that involve
multiple operations (fund, transfer, verify) with automatic
cleanup and state tracking.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.wait import wait_for_confirmation


@dataclass
class ScenarioContext:
    """Mutable state passed through scenario steps."""

    solana: AsyncClient
    rpc: RpcClient
    config: TestConfig
    keypairs: dict[str, Keypair] = field(default_factory=dict)
    pubkeys: dict[str, Pubkey] = field(default_factory=dict)
    signatures: list[str] = field(default_factory=list)
    balances: dict[str, int] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)

    def store(self, key: str, value: Any) -> None:
        self.state[key] = value

    def get(self, key: str) -> Any:
        return self.state[key]

    def get_keypair(self, name: str) -> Keypair:
        return self.keypairs[name]

    def get_pubkey(self, name: str) -> Pubkey:
        if name in self.pubkeys:
            return self.pubkeys[name]
        return self.keypairs[name].pubkey()


StepFn = Callable[[ScenarioContext], Awaitable[None]]


@dataclass
class ScenarioStep:
    """A single step in a scenario."""

    name: str
    action: StepFn


class ScenarioBuilder:
    """Fluent builder for multi-step test scenarios.

    Usage:
        scenario = (ScenarioBuilder("transfer lifecycle")
            .fund("sender", 5_000_000_000)
            .fund("recipient", 0)
            .transfer("sender", "recipient", 1_000_000_000)
            .assert_balance("recipient", 1_000_000_000)
            .assert_balance_decreased("sender", 1_000_000_000)
            .custom("check_signature", check_sig_fn)
            .build())

        await scenario.run(solana_client, rpc_client, test_config)
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._steps: list[ScenarioStep] = []

    def fund(self, account_name: str, lamports: int = 5_000_000_000) -> ScenarioBuilder:
        """Create and fund a named account."""

        async def _fund(ctx: ScenarioContext) -> None:
            kp = Keypair()
            ctx.keypairs[account_name] = kp
            ctx.pubkeys[account_name] = kp.pubkey()
            if lamports > 0:
                resp = await ctx.solana.request_airdrop(kp.pubkey(), lamports)
                sig = str(resp.value)
                await wait_for_confirmation(ctx.config.rpc_url, sig)
                ctx.signatures.append(sig)
            ctx.balances[account_name] = lamports

        self._steps.append(ScenarioStep(f"fund:{account_name}", _fund))
        return self

    def add_keypair(self, name: str) -> ScenarioBuilder:
        """Register an unfunded keypair."""

        async def _add(ctx: ScenarioContext) -> None:
            kp = Keypair()
            ctx.keypairs[name] = kp
            ctx.pubkeys[name] = kp.pubkey()
            ctx.balances[name] = 0

        self._steps.append(ScenarioStep(f"keypair:{name}", _add))
        return self

    def transfer(self, from_name: str, to_name: str, lamports: int) -> ScenarioBuilder:
        """Send a SOL transfer between named accounts."""

        async def _transfer(ctx: ScenarioContext) -> None:
            from solders.message import Message
            from solders.system_program import TransferParams, transfer
            from solders.transaction import Transaction

            sender = ctx.get_keypair(from_name)
            recipient = ctx.get_pubkey(to_name)

            bh_resp = await ctx.solana.get_latest_blockhash()
            blockhash = bh_resp.value.blockhash

            ix = transfer(
                TransferParams(
                    from_pubkey=sender.pubkey(),
                    to_pubkey=recipient,
                    lamports=lamports,
                )
            )
            msg = Message.new_with_blockhash([ix], sender.pubkey(), blockhash)
            tx = Transaction.new_unsigned(msg)
            tx.sign([sender], blockhash)

            resp = await ctx.solana.send_transaction(tx)
            sig = str(resp.value)
            await wait_for_confirmation(ctx.config.rpc_url, sig)
            ctx.signatures.append(sig)

        self._steps.append(ScenarioStep(f"transfer:{from_name}->{to_name}", _transfer))
        return self

    def assert_balance(
        self, account_name: str, expected: int, *, tolerance: int = 0
    ) -> ScenarioBuilder:
        """Assert an account has a specific balance."""

        async def _check(ctx: ScenarioContext) -> None:
            pubkey = ctx.get_pubkey(account_name)
            result = await ctx.solana.get_balance(pubkey)
            actual = result.value
            diff = abs(actual - expected)
            assert diff <= tolerance, (
                f"[{account_name}] balance {actual} != expected {expected} (+-{tolerance})"
            )
            ctx.balances[account_name] = actual

        self._steps.append(ScenarioStep(f"assert_balance:{account_name}", _check))
        return self

    def assert_balance_decreased(self, account_name: str, min_decrease: int = 1) -> ScenarioBuilder:
        """Assert balance decreased from last recorded value."""

        async def _check(ctx: ScenarioContext) -> None:
            pubkey = ctx.get_pubkey(account_name)
            result = await ctx.solana.get_balance(pubkey)
            actual = result.value
            previous = ctx.balances.get(account_name, 0)
            decrease = previous - actual
            assert decrease >= min_decrease, (
                f"[{account_name}] balance decrease {decrease} < {min_decrease} "
                f"(was {previous}, now {actual})"
            )
            ctx.balances[account_name] = actual

        self._steps.append(ScenarioStep(f"assert_decreased:{account_name}", _check))
        return self

    def assert_balance_increased(self, account_name: str, min_increase: int = 1) -> ScenarioBuilder:
        """Assert balance increased from last recorded value."""

        async def _check(ctx: ScenarioContext) -> None:
            pubkey = ctx.get_pubkey(account_name)
            result = await ctx.solana.get_balance(pubkey)
            actual = result.value
            previous = ctx.balances.get(account_name, 0)
            increase = actual - previous
            assert increase >= min_increase, (
                f"[{account_name}] balance increase {increase} < {min_increase} "
                f"(was {previous}, now {actual})"
            )
            ctx.balances[account_name] = actual

        self._steps.append(ScenarioStep(f"assert_increased:{account_name}", _check))
        return self

    def wait_slots(self, count: int = 1) -> ScenarioBuilder:
        """Wait for N slots to pass."""

        async def _wait(ctx: ScenarioContext) -> None:
            slot_resp = await ctx.solana.get_slot()
            start_slot = slot_resp.value
            target = start_slot + count
            for _ in range(count * 10):
                await asyncio.sleep(0.5)
                slot_resp = await ctx.solana.get_slot()
                if slot_resp.value >= target:
                    return
            raise TimeoutError(f"Slots did not advance by {count}")

        self._steps.append(ScenarioStep(f"wait_slots:{count}", _wait))
        return self

    def capture_balance(self, account_name: str) -> ScenarioBuilder:
        """Snapshot current balance for later comparison."""

        async def _capture(ctx: ScenarioContext) -> None:
            pubkey = ctx.get_pubkey(account_name)
            result = await ctx.solana.get_balance(pubkey)
            ctx.balances[account_name] = result.value

        self._steps.append(ScenarioStep(f"capture_balance:{account_name}", _capture))
        return self

    def custom(self, name: str, action: StepFn) -> ScenarioBuilder:
        """Add a custom step."""
        self._steps.append(ScenarioStep(name, action))
        return self

    def build(self) -> Scenario:
        return Scenario(self._name, list(self._steps))


class Scenario:
    """Executable test scenario with step tracking."""

    def __init__(self, name: str, steps: list[ScenarioStep]) -> None:
        self.name = name
        self.steps = steps
        self.completed_steps: list[str] = []
        self.failed_step: str | None = None

    async def run(
        self,
        solana: AsyncClient,
        rpc: RpcClient,
        config: TestConfig,
    ) -> ScenarioContext:
        """Execute all steps in order. Returns context with accumulated state."""
        ctx = ScenarioContext(solana=solana, rpc=rpc, config=config)
        for step in self.steps:
            try:
                await step.action(ctx)
                self.completed_steps.append(step.name)
            except Exception:
                self.failed_step = step.name
                raise
        return ctx
