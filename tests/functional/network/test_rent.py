"""Functional tests: getMinimumBalanceForRentExemption."""

from __future__ import annotations

import pytest

from karstflow_tests.rpc import RpcClient
from tests.helpers.constants import RENT_DATA_SIZES, RENT_DATA_SIZES_IDS


async def test_rent_exemption_zero_bytes(rpc_client: RpcClient) -> None:
    """Rent exemption for 0 bytes of data."""
    lamports = await rpc_client.get_minimum_balance_for_rent_exemption(0)
    assert isinstance(lamports, int)
    assert lamports > 0


@pytest.mark.parametrize("data_size", RENT_DATA_SIZES, ids=RENT_DATA_SIZES_IDS)
async def test_rent_exemption_by_size(rpc_client: RpcClient, data_size: int) -> None:
    """Rent exemption scales with data size."""
    lamports = await rpc_client.get_minimum_balance_for_rent_exemption(data_size)
    assert lamports > 0


async def test_rent_exemption_increases_with_size(rpc_client: RpcClient) -> None:
    """Larger accounts require more lamports for rent exemption."""
    small = await rpc_client.get_minimum_balance_for_rent_exemption(0)
    medium = await rpc_client.get_minimum_balance_for_rent_exemption(1024)
    large = await rpc_client.get_minimum_balance_for_rent_exemption(10240)
    assert small < medium < large


async def test_rent_exemption_deterministic(rpc_client: RpcClient) -> None:
    """Same data size always returns same rent exemption."""
    r1 = await rpc_client.get_minimum_balance_for_rent_exemption(100)
    r2 = await rpc_client.get_minimum_balance_for_rent_exemption(100)
    assert r1 == r2
