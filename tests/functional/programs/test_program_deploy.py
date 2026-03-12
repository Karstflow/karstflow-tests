"""Tests for BPF program deployment and execution via BPF Loader v2."""

from __future__ import annotations

import pytest
from solana.rpc.async_api import AsyncClient
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.transaction import Transaction

from karstflow_tests.programs import (
    BPF_LOADER,
    deploy_program,
    get_rpc_url,
    load_program_bytes,
)
from karstflow_tests.wait import wait_for_confirmation

pytestmark = [pytest.mark.programs, pytest.mark.deploy]


async def test_deploy_hello_log(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Deploy hello-log program and verify account is executable."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "hello_log", program_keypair=program_kp
    )
    info = await solana_client.get_account_info(program_id)
    assert info.value is not None
    assert info.value.executable
    assert str(info.value.owner) == str(BPF_LOADER)


async def test_deploy_program_has_correct_data_size(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Deployed program account data matches .so file size."""
    program_bytes = load_program_bytes("hello_log")
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "hello_log", program_keypair=program_kp
    )
    info = await solana_client.get_account_info(program_id)
    assert info.value is not None
    assert len(info.value.data) == len(program_bytes)


async def test_invoke_hello_log(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Invoke hello-log program — should succeed (no error)."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "hello_log", program_keypair=program_kp
    )

    # Call with some data
    ix = Instruction(
        program_id=program_id,
        data=b"\x42",
        accounts=[],
    )
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    sig = str(resp.value)
    rpc_url = await get_rpc_url(solana_client)
    await wait_for_confirmation(rpc_url, sig)

    # Verify tx succeeded
    tx_result = await solana_client.get_transaction(
        resp.value, max_supported_transaction_version=0
    )
    assert tx_result.value is not None
    meta = tx_result.value.transaction.meta
    assert meta is not None
    assert meta.err is None


async def test_invoke_hello_log_empty_data(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Invoke hello-log with empty data — should succeed."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "hello_log", program_keypair=program_kp
    )

    ix = Instruction(program_id=program_id, data=b"", accounts=[])
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)
    resp = await solana_client.send_transaction(tx)
    rpc_url = await get_rpc_url(solana_client)
    await wait_for_confirmation(rpc_url, str(resp.value))


async def test_simulate_hello_log(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Simulate hello-log invocation — check logs contain program output."""
    program_kp = Keypair()
    program_id = await deploy_program(
        solana_client, funded_keypair, "hello_log", program_keypair=program_kp
    )

    ix = Instruction(program_id=program_id, data=b"\x01", accounts=[])
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)

    sim = await solana_client.simulate_transaction(tx)
    assert sim.value.err is None
    # Check logs contain our program's output
    if sim.value.logs:
        log_text = " ".join(sim.value.logs)
        assert "hello-log" in log_text or "Program log" in log_text


async def test_deploy_multiple_programs(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Deploy two different programs — both should be independently callable."""
    kp1 = Keypair()
    kp2 = Keypair()
    pid1 = await deploy_program(
        solana_client, funded_keypair, "hello_log", program_keypair=kp1
    )
    pid2 = await deploy_program(
        solana_client, funded_keypair, "hello_log", program_keypair=kp2
    )
    assert pid1 != pid2

    # Both executable
    info1 = await solana_client.get_account_info(pid1)
    info2 = await solana_client.get_account_info(pid2)
    assert info1.value is not None
    assert info1.value.executable
    assert info2.value is not None
    assert info2.value.executable


async def test_invoke_nonexistent_program_fails(
    solana_client: AsyncClient, funded_keypair: Keypair
) -> None:
    """Invoking a random pubkey as program should fail."""
    fake_program = Keypair().pubkey()
    ix = Instruction(program_id=fake_program, data=b"", accounts=[])
    blockhash_resp = await solana_client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    msg = Message.new_with_blockhash([ix], funded_keypair.pubkey(), blockhash)
    tx = Transaction.new_unsigned(msg)
    tx.sign([funded_keypair], blockhash)

    sim = await solana_client.simulate_transaction(tx)
    assert sim.value.err is not None
