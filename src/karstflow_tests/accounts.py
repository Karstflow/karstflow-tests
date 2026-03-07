"""Keypair and account factory helpers."""

from __future__ import annotations

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from karstflow_tests.rpc import RpcClient
from karstflow_tests.wait import wait_for_confirmation


async def create_funded_keypair(
    rpc: RpcClient,
    lamports: int = 10_000_000_000,
) -> Keypair:
    """Create a new keypair and fund it via airdrop."""
    kp = Keypair()
    sig = await rpc.request_airdrop(str(kp.pubkey()), lamports)
    await wait_for_confirmation(rpc.url, sig)
    return kp


async def get_balance_lamports(rpc: RpcClient, pubkey: Pubkey | str) -> int:
    """Get account balance in lamports."""
    result = await rpc.get_balance(str(pubkey))
    return result["value"]
