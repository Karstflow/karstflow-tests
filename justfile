# karstflow-tests task runner

default:
    @just --list

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

# CI pipeline
ci: fmt-check lint typecheck

# Collect tests without running
collect:
    uv run pytest --co

# Start single validator node via Docker
node-up:
    docker compose -f docker-compose.single.yml up -d

# Stop single validator node
node-down:
    docker compose -f docker-compose.single.yml down

# Start 3-node cluster
cluster-up:
    docker compose up -d

# Stop cluster
cluster-down:
    docker compose down

# Build validator Docker image
build-image:
    cd ../karstflow && docker build -t karstflow:latest .
