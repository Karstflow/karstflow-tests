# karstflow-tests

End-to-end and load testing suite for the karstflow validator. Tests interact with the validator as a black box via JSON-RPC and WebSocket APIs using the official Solana Python client.

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

## Project Structure

```
karstflow-tests/
├── pyproject.toml              # Dependencies and pytest config
├── justfile                    # Task runner commands
├── docker-compose.yml          # 3-node cluster
├── docker-compose.single.yml   # Single node for development
│
├── src/karstflow_tests/        # Shared test utilities
│   ├── rpc.py                  # Typed JSON-RPC client
│   ├── ws.py                   # WebSocket subscription helper
│   ├── node.py                 # Node/cluster lifecycle manager
│   ├── accounts.py             # Keypair/account factories
│   ├── transactions.py         # Transaction builders
│   └── wait.py                 # Polling/retry utilities
│
├── tests/
│   ├── conftest.py             # Root fixtures
│   ├── smoke/                  # Health and genesis checks
│   ├── functional/             # RPC method tests
│   ├── websocket/              # Subscription tests
│   ├── integration/            # Multi-node cluster tests
│   └── load/                   # Locust load tests + benchmarks
│
└── fixtures/                   # Static test data
    ├── programs/               # Pre-compiled BPF programs
    └── accounts/               # Serialized account snapshots
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

# Full CI check
just ci
```

## Tech Stack

- **pytest** — test framework with async support
- **httpx** — async HTTP client for JSON-RPC
- **websockets** — WebSocket client for subscriptions
- **solana-py** + **solders** — official Solana Python client
- **Locust** — load testing framework
- **pytest-benchmark** — microbenchmark harness
