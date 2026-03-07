"""Shared test utilities for karstflow validator E2E testing."""

from karstflow_tests.accounts import create_funded_keypair, get_balance_lamports
from karstflow_tests.assertions import (
    assert_account_exists,
    assert_account_not_exists,
    assert_balance,
    assert_balance_decreased,
    assert_balance_increased,
    assert_rpc_error,
    assert_slot_advances,
    assert_transaction_confirmed,
)
from karstflow_tests.client import ValidatorClient
from karstflow_tests.config import Commitment, RetryPolicy, TestConfig, load_config
from karstflow_tests.factories import (
    KeypairFactory,
    TransactionFactory,
    invalid_pubkey_strings,
    known_program_ids,
    lamport_amounts,
    rpc_methods_readonly,
    rpc_methods_with_pubkey_param,
)
from karstflow_tests.node import ClusterHandle, NodeHandle, NodeManager
from karstflow_tests.rpc import RpcClient
from karstflow_tests.transactions import build_and_send_transfer
from karstflow_tests.types import (
    AccountInfo,
    BlockProduction,
    EpochInfo,
    RpcCallError,
    RpcErrorData,
    RpcResponse,
    SignatureStatus,
)
from karstflow_tests.wait import wait_for_confirmation, wait_for_health
from karstflow_tests.ws import WsClient, WsError, WsSubscription

__all__ = [
    # Types
    "AccountInfo",
    "BlockProduction",
    # Node management
    "ClusterHandle",
    # Config
    "Commitment",
    "EpochInfo",
    # Factories
    "KeypairFactory",
    "NodeHandle",
    "NodeManager",
    "RetryPolicy",
    "RpcCallError",
    "RpcClient",
    "RpcErrorData",
    "RpcResponse",
    "SignatureStatus",
    "TestConfig",
    "TransactionFactory",
    # Client
    "ValidatorClient",
    "WsClient",
    "WsError",
    "WsSubscription",
    # Assertions
    "assert_account_exists",
    "assert_account_not_exists",
    "assert_balance",
    "assert_balance_decreased",
    "assert_balance_increased",
    "assert_rpc_error",
    "assert_slot_advances",
    "assert_transaction_confirmed",
    # Helpers
    "build_and_send_transfer",
    "create_funded_keypair",
    "get_balance_lamports",
    "invalid_pubkey_strings",
    "known_program_ids",
    "lamport_amounts",
    "load_config",
    "rpc_methods_readonly",
    "rpc_methods_with_pubkey_param",
    "wait_for_confirmation",
    "wait_for_health",
]
