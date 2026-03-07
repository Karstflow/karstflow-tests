"""Functional tests: advanced multi-step scenarios with state verification.

Uses ScenarioBuilder and StateCapture together for complex test flows.
"""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.config import TestConfig
from karstflow_tests.rpc import RpcClient
from karstflow_tests.scenarios import ScenarioBuilder, ScenarioContext
from karstflow_tests.state import StateCapture
from karstflow_tests.wait import wait_for_confirmation


async def test_scenario_with_state_capture(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Scenario that uses StateCapture for before/after verification."""
    capture = StateCapture(solana_client, rpc_client)

    async def setup_tracking(ctx: ScenarioContext) -> None:
        capture.track_account("sender", ctx.get_pubkey("sender"))
        capture.track_account("receiver", ctx.get_pubkey("receiver"))
        ctx.store("before", await capture.snapshot())

    async def verify_state(ctx: ScenarioContext) -> None:
        after = await capture.snapshot()
        diff = StateCapture.diff(ctx.get("before"), after)
        assert diff.has_changes
        assert "receiver" in diff.balance_changes
        assert diff.balance_changes["receiver"] == 2_000_000_000

    scenario = (
        ScenarioBuilder("state capture flow")
        .fund("sender", 5_000_000_000)
        .add_keypair("receiver")
        .custom("setup_tracking", setup_tracking)
        .transfer("sender", "receiver", 2_000_000_000)
        .custom("verify_state", verify_state)
        .build()
    )
    await scenario.run(solana_client, rpc_client, test_config)


async def test_chain_of_transfers(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Chain: A -> B -> C, verify only C has the final balance."""

    async def transfer_b_to_c(ctx: ScenarioContext) -> None:
        from solders.message import Message
        from solders.system_program import TransferParams, transfer
        from solders.transaction import Transaction

        sender = ctx.get_keypair("bob")
        recipient = ctx.get_pubkey("charlie")
        bh = await ctx.solana.get_latest_blockhash()
        ix = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=recipient,
                lamports=500_000_000,
            )
        )
        msg = Message.new_with_blockhash([ix], sender.pubkey(), bh.value.blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([sender], bh.value.blockhash)
        resp = await ctx.solana.send_transaction(tx)
        await wait_for_confirmation(ctx.config.rpc_url, str(resp.value))

    scenario = (
        ScenarioBuilder("chain transfer")
        .fund("alice", 5_000_000_000)
        .add_keypair("bob")
        .add_keypair("charlie")
        .transfer("alice", "bob", 1_000_000_000)
        .assert_balance("bob", 1_000_000_000)
        .custom("b_to_c", transfer_b_to_c)
        .assert_balance("charlie", 500_000_000)
        .build()
    )
    await scenario.run(solana_client, rpc_client, test_config)


async def test_scenario_tracks_all_signatures(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """All transaction signatures are tracked in context."""
    scenario = (
        ScenarioBuilder("sig tracking")
        .fund("a", 5_000_000_000)
        .fund("b", 5_000_000_000)
        .transfer("a", "b", 100_000)
        .transfer("b", "a", 50_000)
        .build()
    )
    ctx = await scenario.run(solana_client, rpc_client, test_config)
    # 2 airdrops + 2 transfers = 4 signatures
    assert len(ctx.signatures) == 4
    for sig in ctx.signatures:
        assert len(sig) > 40


async def test_scenario_fund_then_drain(
    solana_client: AsyncClient,
    rpc_client: RpcClient,
    test_config: TestConfig,
) -> None:
    """Fund an account then transfer most of it away."""
    scenario = (
        ScenarioBuilder("fund and drain")
        .fund("source", 3_000_000_000)
        .add_keypair("sink")
        .capture_balance("source")
        .transfer("source", "sink", 2_999_000_000)
        .assert_balance_decreased("source", 2_999_000_000)
        .assert_balance("sink", 2_999_000_000)
        .build()
    )
    await scenario.run(solana_client, rpc_client, test_config)
