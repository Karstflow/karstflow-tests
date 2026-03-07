"""Scenario-based transaction tests using ScenarioBuilder.

These tests demonstrate complex multi-step operations orchestrated
through the scenario framework.
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.scenarios import ScenarioBuilder, ScenarioContext


async def test_simple_transfer_scenario(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Fund sender, transfer to recipient, verify balances."""
    scenario = (
        ScenarioBuilder("simple transfer")
        .fund("sender", 5_000_000_000)
        .add_keypair("recipient")
        .transfer("sender", "recipient", 1_000_000_000)
        .assert_balance("recipient", 1_000_000_000)
        .assert_balance_decreased("sender", 1_000_000_000)
        .build()
    )
    ctx = await scenario.run(solana_client, rpc_client, test_config)
    assert len(ctx.signatures) == 2  # airdrop + transfer
    assert len(scenario.completed_steps) == 5


async def test_multi_recipient_scenario(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Fund sender, transfer to 3 recipients, verify all balances."""
    scenario = (
        ScenarioBuilder("multi recipient")
        .fund("sender", 10_000_000_000)
        .add_keypair("alice")
        .add_keypair("bob")
        .add_keypair("charlie")
        .transfer("sender", "alice", 1_000_000_000)
        .transfer("sender", "bob", 2_000_000_000)
        .transfer("sender", "charlie", 500_000_000)
        .assert_balance("alice", 1_000_000_000)
        .assert_balance("bob", 2_000_000_000)
        .assert_balance("charlie", 500_000_000)
        .build()
    )
    ctx = await scenario.run(solana_client, rpc_client, test_config)
    assert len(ctx.signatures) == 4  # 1 airdrop + 3 transfers


async def test_round_trip_scenario(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Transfer from A to B, then B back to A."""
    scenario = (
        ScenarioBuilder("round trip")
        .fund("alice", 5_000_000_000)
        .fund("bob", 5_000_000_000)
        .capture_balance("alice")
        .capture_balance("bob")
        .transfer("alice", "bob", 1_000_000_000)
        .assert_balance_increased("bob", 1_000_000_000)
        .capture_balance("alice")
        .capture_balance("bob")
        .transfer("bob", "alice", 1_000_000_000)
        .assert_balance_increased("alice", 1_000_000_000)
        .build()
    )
    await scenario.run(solana_client, rpc_client, test_config)
    assert len(scenario.completed_steps) == 10


async def test_scenario_custom_step(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Scenario with a custom verification step."""

    async def verify_slot_advanced(ctx: ScenarioContext) -> None:
        slot = await ctx.rpc.get_slot()
        assert slot > 0
        ctx.store("verified_slot", slot)

    scenario = (
        ScenarioBuilder("custom step")
        .fund("account", 1_000_000_000)
        .custom("verify_slot", verify_slot_advanced)
        .build()
    )
    ctx = await scenario.run(solana_client, rpc_client, test_config)
    assert ctx.get("verified_slot") > 0


async def test_scenario_with_wait_slots(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Scenario that waits for slots to advance."""

    async def record_slot(ctx: ScenarioContext) -> None:
        slot = await ctx.rpc.get_slot()
        ctx.store("slot_before", slot)

    async def check_slot_advanced(ctx: ScenarioContext) -> None:
        slot = await ctx.rpc.get_slot()
        assert slot > ctx.get("slot_before")

    scenario = (
        ScenarioBuilder("wait slots")
        .custom("record_slot", record_slot)
        .wait_slots(2)
        .custom("check_advanced", check_slot_advanced)
        .build()
    )
    await scenario.run(solana_client, rpc_client, test_config)
