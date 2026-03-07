"""Keypair and account factory helpers."""

from __future__ import annotations

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from karstflow_tests.wait import wait_for_confirmation


async def create_funded_keypair(
    client: AsyncClient,
    lamports: int = 10_000_000_000,
) -> Keypair:
    """Create a new keypair and fund it via airdrop."""
    kp = Keypair()
    resp = await client.request_airdrop(kp.pubkey(), lamports)
    endpoint = str(client._provider.endpoint_uri)
    await wait_for_confirmation(endpoint, str(resp.value))
    return kp


async def get_balance_lamports(client: AsyncClient, pubkey: Pubkey | str) -> int:
    """Get account balance in lamports."""
    if isinstance(pubkey, str):
        pubkey = Pubkey.from_string(pubkey)
    result = await client.get_balance(pubkey)
    return result.value
