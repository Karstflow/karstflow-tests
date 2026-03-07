"""Functional tests: getLeaderSchedule."""

from __future__ import annotations

from karstflow_tests.rpc import RpcClient


async def test_leader_schedule_exists(rpc_client: RpcClient) -> None:
    """getLeaderSchedule returns a schedule mapping."""
    schedule = await rpc_client.get_leader_schedule()
    assert schedule is not None
    assert isinstance(schedule, dict)
    assert len(schedule) >= 1


async def test_leader_schedule_has_slot_arrays(rpc_client: RpcClient) -> None:
    """Each leader in schedule has a list of slot indices."""
    schedule = await rpc_client.get_leader_schedule()
    assert schedule is not None
    for pubkey, slots in schedule.items():
        assert isinstance(pubkey, str)
        assert isinstance(slots, list)
        assert all(isinstance(s, int) for s in slots)


async def test_leader_schedule_validator_present(rpc_client: RpcClient) -> None:
    """The node's identity should appear in the leader schedule."""
    identity = await rpc_client.get_identity()
    schedule = await rpc_client.get_leader_schedule()
    assert schedule is not None
    # In dev mode, the validator should be the only leader
    assert identity["identity"] in schedule
