# karstflow-tests task runner

default:
    @just --list

# ── Test layers ──────────────────────────────────────────────────────

# Run smoke tests (quick health checks)
smoke:
    uv run pytest tests/smoke -v -m smoke

# Run functional RPC tests
functional:
    uv run pytest tests/functional -v -m functional

# Run WebSocket subscription tests
websocket:
    uv run pytest tests/websocket -v -m websocket

# Run multi-node integration tests
integration:
    uv run pytest tests/integration -v -m integration --timeout=120

# Run load/performance tests
load:
    uv run pytest tests/load -v -m load --timeout=300

# Run all tests except load
all:
    uv run pytest tests/smoke tests/functional tests/websocket tests/integration -v

# ── Named suites ────────────────────────────────────────────────────

# Run quick feedback suite (smoke + basic functional, < 2 min)
quick:
    uv run pytest tests/smoke tests/functional/accounts tests/functional/blocks -v --timeout=30

# Run pre-merge gate (smoke + functional + websocket, no cluster)
pre-merge:
    uv run pytest tests/smoke tests/functional tests/websocket -v --timing-report

# Run full suite with coverage and timing reports
full:
    uv run pytest tests/smoke tests/functional tests/websocket tests/integration -v --rpc-coverage --timing-report --timeout=120

# Run RPC compatibility suite with coverage report
rpc-compat:
    uv run pytest tests/functional -v --rpc-coverage --timing-report

# Run token lifecycle suite
token-lifecycle:
    uv run pytest tests/functional/programs/test_token_program.py tests/functional/programs/test_token_lifecycle.py tests/functional/programs/test_token_advanced.py tests/functional/accounts/test_token_queries.py -v

# Run transaction lifecycle suite
tx-lifecycle:
    uv run pytest tests/functional/transactions/test_send_transaction.py tests/functional/transactions/test_transfer.py tests/functional/transactions/test_get_transaction.py tests/functional/transactions/test_transaction_lifecycle.py tests/functional/transactions/test_commitment_lifecycle.py -v

# List available test suites
suites:
    @uv run python -c "from karstflow_tests.suites import suite_help; print(suite_help())"

# ── Test groups (functional subsets) ─────────────────────────────────

# Run account tests (getBalance, getAccountInfo, airdrop, etc.)
test-accounts:
    uv run pytest tests/functional/accounts -v

# Run transaction tests (transfer, simulate, signatures, lifecycle)
test-transactions:
    uv run pytest tests/functional/transactions -v

# Run block tests (getBlock, slot, epoch, blockhash, block production)
test-blocks:
    uv run pytest tests/functional/blocks -v

# Run network tests (supply, inflation, rent, performance, fees)
test-network:
    uv run pytest tests/functional/network -v

# Run cluster info tests (nodes, leader schedule, vote accounts)
test-cluster-info:
    uv run pytest tests/functional/cluster_info -v

# Run error/edge case tests (invalid params, unknown methods, boundaries)
test-errors:
    uv run pytest tests/functional/errors -v

# Run program tests (native programs, sysvars, token, memo, compute budget)
test-programs:
    uv run pytest tests/functional/programs -v -m programs

# Run token lifecycle tests only
test-tokens:
    uv run pytest tests/functional/programs/test_token_lifecycle.py -v

# Run system program tests only
test-system:
    uv run pytest tests/functional/programs/test_system_program.py tests/functional/programs/test_system_program_deep.py -v

# Run validator behavior tests
test-validator:
    uv run pytest tests/functional/programs/test_validator_behavior.py -v

# ── Test utilities ───────────────────────────────────────────────────

# Run specific test by keyword
test-k KEYWORD:
    uv run pytest -v -k "{{KEYWORD}}"

# Run with verbose output and no capture
test-debug *ARGS:
    uv run pytest -v -s --tb=long {{ARGS}}

# Run a specific test file
test-file FILE:
    uv run pytest {{FILE}} -v

# Run tests matching a marker
test-mark MARKER:
    uv run pytest -v -m "{{MARKER}}"

# Run with timing report
test-timed *ARGS:
    uv run pytest -v --timing-report {{ARGS}}

# Run with RPC coverage report
test-coverage *ARGS:
    uv run pytest -v --rpc-coverage {{ARGS}}

# Run with both reports
test-full-report *ARGS:
    uv run pytest -v --rpc-coverage --timing-report {{ARGS}}

# ── Comparison testing ──────────────────────────────────────────────

# Run comparison tests against Solana reference (set KARSTFLOW_REFERENCE_URL)
compare *ARGS:
    uv run pytest tests/comparison -v {{ARGS}}

# Run basic RPC comparison against reference
compare-basic:
    uv run pytest tests/comparison/test_rpc_compat.py -v

# Run structural comparison (response shapes only)
compare-structure:
    uv run pytest tests/comparison/test_response_structure.py -v

# ── Quality ──────────────────────────────────────────────────────────

# Run ruff linter
lint:
    uv run ruff check src/ tests/

# Run ruff formatter check
fmt-check:
    uv run ruff format --check src/ tests/

# Format code
fmt:
    uv run ruff format src/ tests/

# Type check
typecheck:
    uv run mypy src/

# CI pipeline (lint + format + typecheck)
ci: fmt-check lint typecheck

# Fix auto-fixable lint issues
fix:
    uv run ruff check --fix src/ tests/

# ── Discovery ────────────────────────────────────────────────────────

# Collect tests without running (show count)
collect:
    uv run pytest --co -q

# Show test markers
markers:
    uv run pytest --markers

# List available fixtures
fixtures:
    uv run pytest --fixtures -q

# Show test count per directory
test-stats:
    @echo "=== Test Distribution ===" && \
    echo "smoke:        $(uv run pytest tests/smoke --co -q 2>/dev/null | tail -1)" && \
    echo "accounts:     $(uv run pytest tests/functional/accounts --co -q 2>/dev/null | tail -1)" && \
    echo "transactions: $(uv run pytest tests/functional/transactions --co -q 2>/dev/null | tail -1)" && \
    echo "blocks:       $(uv run pytest tests/functional/blocks --co -q 2>/dev/null | tail -1)" && \
    echo "cluster_info: $(uv run pytest tests/functional/cluster_info --co -q 2>/dev/null | tail -1)" && \
    echo "network:      $(uv run pytest tests/functional/network --co -q 2>/dev/null | tail -1)" && \
    echo "errors:       $(uv run pytest tests/functional/errors --co -q 2>/dev/null | tail -1)" && \
    echo "programs:     $(uv run pytest tests/functional/programs --co -q 2>/dev/null | tail -1)" && \
    echo "websocket:    $(uv run pytest tests/websocket --co -q 2>/dev/null | tail -1)" && \
    echo "comparison:   $(uv run pytest tests/comparison --co -q 2>/dev/null | tail -1)" && \
    echo "==========================" && \
    echo "TOTAL:        $(uv run pytest --co -q 2>/dev/null | tail -1)"

# ── Docker: single node ─────────────────────────────────────────────

# Start single validator node via Docker
node-up:
    docker compose -f docker-compose.single.yml up -d

# Stop single validator node
node-down:
    docker compose -f docker-compose.single.yml down

# View single node logs
node-logs:
    docker compose -f docker-compose.single.yml logs -f

# Restart single node (clean state)
node-restart:
    docker compose -f docker-compose.single.yml down -v && docker compose -f docker-compose.single.yml up -d

# Build and start (clean rebuild + start)
node-fresh: build-image node-restart

# ── Docker: cluster ─────────────────────────────────────────────────

# Start 3-node cluster
cluster-up:
    docker compose up -d

# Stop cluster
cluster-down:
    docker compose down

# View cluster logs
cluster-logs:
    docker compose logs -f

# Restart cluster (clean state)
cluster-restart:
    docker compose down -v && docker compose up -d

# ── Load testing ─────────────────────────────────────────────────────

# Run Locust web UI (open http://localhost:8089)
locust:
    uv run locust -f tests/load/locustfile.py --host http://localhost:8899

# Run Locust headless: 10 users, 2/s spawn rate, 60s duration
locust-headless USERS="10" RATE="2" TIME="60s":
    uv run locust -f tests/load/locustfile.py --host http://localhost:8899 --headless -u {{USERS}} -r {{RATE}} -t {{TIME}}

# ── Build ────────────────────────────────────────────────────────────

# Build validator Docker image
build-image:
    cd ../karstflow && docker build -t karstflow:latest .

# Sync Python dependencies
sync:
    uv sync

# ── Workflows ────────────────────────────────────────────────────────

# Full CI workflow: lint + typecheck + node-up + smoke + node-down
ci-e2e: ci node-up
    @echo "Waiting for node to be ready..." && sleep 5
    uv run pytest tests/smoke -v -m smoke || (just node-down && exit 1)
    just node-down
