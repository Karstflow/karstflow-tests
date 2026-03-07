# karstflow-tests

End-to-end and load testing suite for the karstflow validator. Tests interact with the validator as a black box via JSON-RPC and WebSocket APIs using the official Solana Python client.

**433 tests** across 11 test groups covering RPC methods, system programs, SPL token lifecycle, WebSocket subscriptions, commitment levels, encoding formats, blockhash validity, stress/robustness, multi-node integration, load testing, and advanced test tooling.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for running validator nodes)
- [just](https://github.com/casey/just) task runner

## Quick Start

```bash
# Install dependencies
uv sync

# Build the validator Docker image
just build-image

# Start a single validator node
just node-up

# Run smoke tests
just smoke

# Run all functional tests
just functional

# Stop the node
just node-down
```

## Test Layers

| Layer | Command | Description |
|---|---|---|
| Smoke | `just smoke` | Quick health checks (< 30s) |
| Functional | `just functional` | Single-node RPC method coverage |
| WebSocket | `just websocket` | Subscription notification tests |
| Integration | `just integration` | Multi-node cluster tests |
| Load | `just load` | Performance and throughput tests |
| All | `just all` | Everything except load tests |

## Test Groups

Run specific functional test groups:

| Group | Command | Tests | Coverage |
|---|---|---|---|
| Accounts | `just test-accounts` | 66 | getBalance, getAccountInfo, airdrop, getLargestAccounts, getProgramAccounts, encoding, request builder, state capture |
| Transactions | `just test-transactions` | 41 | transfer, sendTransaction, simulate, signatures, lifecycle, multi-instruction, nonce, scenarios, commitment lifecycle |
| Blocks | `just test-blocks` | 45 | getBlock, getSlot, epoch, blockhash, blockProduction, blockCommitment, txCount, commitment levels, blockhash validity |
| Network | `just test-network` | 26 | supply, inflation, rent, performance, prioritization fees, slot leaders |
| Cluster Info | `just test-cluster-info` | 10 | clusterNodes, leaderSchedule, voteAccounts |
| Errors | `just test-errors` | 40 | invalid params, unknown methods, edge cases, concurrent ops, batch limits, stress tests |
| Programs | `just test-programs` | 129 | native programs, sysvars, SPL token lifecycle + advanced, memo, compute budget, vote, stake |
| WebSocket | `just websocket` | 27 | slot, logs, account, root, signature, program subscriptions, advanced patterns |
| Smoke | `just smoke` | 8 | health, version, genesis, batch |
| Integration | `just integration` | 18 | multi-node cluster: genesis hash, slot convergence, cross-node state, transactions, consistency |
| Load | `just load` | 6 | throughput benchmarks: getSlot, getHealth, getVersion, batch, getBalance, mixed reads |

Additional targeted commands:

```bash
just test-tokens       # SPL Token lifecycle only
just test-system       # System program tests only
just test-validator    # Validator behavior tests
just test-k "memo"     # Run tests matching keyword
just test-mark slow    # Run tests with specific marker
just test-file tests/functional/programs/test_vote_program.py
just test-stats        # Show test distribution per group

# Load testing with Locust
just locust            # Web UI at http://localhost:8089
just locust-headless   # 10 users, 2/s spawn, 60s duration
just locust-headless 50 5 120s  # Custom: 50 users, 5/s spawn, 120s

# RPC method coverage report
uv run pytest tests/smoke -v --rpc-coverage
```

## Project Structure

```
karstflow-tests/
├── pyproject.toml              # Dependencies and pytest config
├── justfile                    # 35+ task runner commands
├── docker-compose.yml          # 3-node cluster
├── docker-compose.single.yml   # Single node for development
│
├── src/karstflow_tests/        # Shared test utilities (18 modules)
│   ├── client.py               # ValidatorClient unified facade
│   ├── rpc.py                  # Typed JSON-RPC client (45+ method wrappers, RequestBuilder exec)
│   ├── ws.py                   # WebSocket client with unsubscribe dispatch
│   ├── config.py               # TestConfig, Commitment, RetryPolicy
│   ├── types.py                # RpcResponse, EpochInfo, AccountInfo, SignatureStatus
│   ├── assertions.py           # 8 domain-specific assertion helpers
│   ├── factories.py            # KeypairFactory, TransactionFactory, parametrization data
│   ├── request_builder.py      # Fluent RequestBuilder for custom RPC requests
│   ├── scenarios.py            # ScenarioBuilder for multi-step test orchestration
│   ├── state.py                # StateCapture, ValidatorSnapshot, StateDiff
│   ├── coverage.py             # RPC method coverage tracking (56 methods)
│   ├── programs.py             # Program helpers: memo, CreateAccount, ComputeBudget, nonce
│   ├── token.py                # SPL Token lifecycle: mint, transfer, burn, close
│   ├── accounts.py             # Account creation and balance helpers
│   ├── transactions.py         # Transaction builder utilities
│   ├── node.py                 # Node/cluster lifecycle manager
│   └── wait.py                 # Polling/retry utilities
│
├── tests/
│   ├── conftest.py             # Root fixtures (11 fixtures)
│   ├── helpers/
│   │   ├── setup.py            # Reusable setup helpers (funded_sender, transfer_pair)
│   │   └── constants.py        # Centralized test constants and parametrization data
│   ├── smoke/                  # Health and genesis checks (8 tests)
│   ├── functional/
│   │   ├── accounts/           # Account RPC tests (42 tests)
│   │   ├── transactions/       # Transaction tests (30 tests)
│   │   ├── blocks/             # Block and slot tests (25 tests)
│   │   ├── cluster_info/       # Cluster info tests (10 tests)
│   │   ├── network/            # Network info tests (26 tests)
│   │   ├── errors/             # Error handling + edge cases + stress (40 tests)
│   │   └── programs/           # Program tests (121 tests)
│   │       ├── test_native_programs.py     # 9 native + 2 SPL + 2 precompile
│   │       ├── test_sysvars.py             # 8 sysvar accounts
│   │       ├── test_token_lifecycle.py     # Full SPL Token lifecycle
│   │       ├── test_memo.py               # Memo program execution
│   │       ├── test_compute_budget.py      # ComputeBudget instructions
│   │       ├── test_system_program.py      # CreateAccount operations
│   │       ├── test_system_program_deep.py # Transfer edge cases, error conditions
│   │       ├── test_vote_program.py        # Vote accounts inspection
│   │       ├── test_stake_program.py       # Stake queries
│   │       ├── test_validator_behavior.py  # Slot progression, fees, leader schedule
│   │       ├── test_config_program.py      # Config program
│   │       ├── test_bpf_loader.py          # BPF Loader accounts
│   │       ├── test_token_program.py       # Token program existence
│   │       └── test_address_lookup_table.py # ALT program
│   ├── websocket/              # WebSocket subscription tests (16 tests)
│   ├── integration/            # Multi-node cluster tests (18 tests)
│   ├── load/                   # Locust load tests + throughput benchmarks (6 tests)
│   └── plugins/                # Pytest plugins (RPC coverage reporting)
│
└── fixtures/                   # Static test data
```

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `KARSTFLOW_RPC_URL` | `http://localhost:8899` | Validator RPC endpoint |
| `KARSTFLOW_WS_URL` | `ws://localhost:8900` | Validator WebSocket endpoint |

## Docker

Build the validator image from the main karstflow project:

```bash
just build-image
```

Run a single development node:

```bash
just node-up    # start
just node-down  # stop
```

Run a 3-node cluster:

```bash
just cluster-up    # start
just cluster-down  # stop
```

## Development

```bash
# Lint
just lint

# Format
just fmt

# Type check
just typecheck

# Full CI check (lint + format + typecheck)
just ci

# Collect tests and show count
just collect

# Show test distribution per group
just test-stats
```

## Tech Stack

- **pytest** — test framework with async support (pytest-asyncio)
- **httpx** — async HTTP client for JSON-RPC
- **websockets** — WebSocket client for subscriptions
- **solana-py** + **solders** — official Solana Python client (primary SDK)
- **Locust** — load testing framework
- **pytest-benchmark** — microbenchmark harness
- **ruff** — linter (16 rule groups) + formatter
- **mypy** — strict type checking

## License

Copyright (c) 2025-2026 boogvar. All rights reserved.
