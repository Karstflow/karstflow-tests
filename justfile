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

# Run specific test by keyword
test-k KEYWORD:
    uv run pytest -v -k "{{KEYWORD}}"

# Run with verbose output and no capture
test-debug *ARGS:
    uv run pytest -v -s --tb=long {{ARGS}}

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

# Collect tests without running
collect:
    uv run pytest --co

# Show test markers
markers:
    uv run pytest --markers

# List available fixtures
fixtures:
    uv run pytest --fixtures -q

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

# ── Build ────────────────────────────────────────────────────────────

# Build validator Docker image
build-image:
    cd ../karstflow && docker build -t karstflow:latest .

# Sync Python dependencies
sync:
    uv sync
