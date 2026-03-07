"""Functional tests: getEpochInfo, getEpochSchedule."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient

from karstflow_tests.client import ValidatorClient
from karstflow_tests.rpc import RpcClient
from karstflow_tests.types import EpochInfo


async def test_epoch_info_fields(rpc_client: RpcClient) -> None:
    """getEpochInfo returns all expected fields."""
    raw = await rpc_client.get_epoch_info()
    info = EpochInfo.from_dict(raw)
    assert info.epoch >= 0
    assert info.slots_in_epoch > 0
    assert info.slot_index >= 0
    assert info.slot_index < info.slots_in_epoch
    assert info.absolute_slot >= 0
    assert info.block_height >= 0


async def test_epoch_schedule(rpc_client: RpcClient) -> None:
    """getEpochSchedule returns schedule parameters."""
    result = await rpc_client.get_epoch_schedule()
    assert "slotsPerEpoch" in result
    assert "warmup" in result
    assert isinstance(result["slotsPerEpoch"], int)
    assert result["slotsPerEpoch"] > 0


async def test_epoch_info_via_validator_client(test_client: ValidatorClient) -> None:
    """ValidatorClient.get_epoch_info returns parsed model."""
    info = await test_client.get_epoch_info()
    assert info.epoch >= 0
    assert info.slots_in_epoch > 0


async def test_epoch_info_consistency(solana_client: AsyncClient, rpc_client: RpcClient) -> None:
    """Epoch info from solana-py and raw RPC should be consistent."""
    raw = await rpc_client.get_epoch_info()
    epoch_raw = raw["epoch"]

    # solana-py
    result = await solana_client.get_epoch_info()
    epoch_sdk = result.value.epoch

    assert epoch_raw == epoch_sdk
