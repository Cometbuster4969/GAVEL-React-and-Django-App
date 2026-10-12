#!/bin/bash
set -e

MODE="${1:-}"

log_info() { echo -e "\033[0;32m[INFO]\033[0m $1"; }
log_warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

setup_env() {
    for file in .env frontend/.env backend/.env; do
        example="${file}.example"
        if [ -f "$example" ] && [ ! -f "$file" ]; then
            cp "$example" "$file"
            log_info "Created $file"
        fi
    done
}

MONGO_HOST="127.0.0.1"
MONGO_PORT="27017"

mongo_is_reachable() {
    (exec 3<>"/dev/tcp/${MONGO_HOST}/${MONGO_PORT}") >/dev/null 2>&1
}

check_mongo() {
    if mongo_is_reachable; then
        log_info "MongoDB is already reachable on ${MONGO_PORT}"
        return
    fi
    log_warn "MongoDB is not reachable on ${MONGO_PORT}; attempting to start local mongod"
    if [ -f /etc/mongod.conf ]; then
        mongod --config /etc/mongod.conf --fork >/dev/null 2>&1 || true
    else
        mkdir -p .mongodb
        mongod --dbpath .mongodb --bind_ip "$MONGO_HOST" --port "$MONGO_PORT" --fork --logpath .mongodb/mongod.log >/dev/null 2>&1 || true
    fi
    if mongo_is_reachable; then
        log_info "MongoDB is now reachable on ${MONGO_PORT}"
        return
    fi
    log_error "MongoDB did not answer on ${MONGO_HOST}:${MONGO_PORT} within the startup check."
    log_error "Gavel requires a running MongoDB 8+ instance. It will not fall back to an in-memory database."
    log_error "Start mongod and re-run setup."
    exit 1
}

setup_python() {
    if [ ! -d ".venv" ]; then
        log_info "Creating .venv with Python 3.12"
        if command -v uv >/dev/null 2>&1; then
            uv venv --python 3.12 .venv 2>&1 || uv venv --python 3.11 .venv 2>&1 || python3 -m venv .venv
        elif [ -f ".venv/bin/uv" ]; then
            .venv/bin/uv venv --python 3.12 .venv 2>&1 || .venv/bin/uv venv --python 3.11 .venv 2>&1 || python3 -m venv .venv
        else
            python3 -m venv .venv 2>&1 || python3.12 -m venv .venv 2>&1 || python3.11 -m venv .venv
        fi
    fi
    if [ -f ".venv/bin/python" ]; then
        if [ -f ".venv/bin/uv" ]; then
            .venv/bin/uv pip install --python .venv/bin/python -r backend/requirements.txt --quiet 2>&1 || .venv/bin/pip install -r backend/requirements.txt --quiet
        elif command -v uv >/dev/null 2>&1; then
            uv pip install --python .venv/bin/python -r backend/requirements.txt --quiet 2>&1 || .venv/bin/pip install -r backend/requirements.txt --quiet
        else
            .venv/bin/pip install -r backend/requirements.txt --quiet
        fi
    elif command -v uv >/dev/null 2>&1; then
        uv pip install --system -r backend/requirements.txt --quiet 2>&1 || pip install -r backend/requirements.txt --quiet
    else
        pip install -r backend/requirements.txt --quiet 2>&1 || pip3 install -r backend/requirements.txt --quiet
    fi
    log_info "Python dependencies ready"
}

seed_database() {
    log_info "Seeding Gavel database"
    if command -v bun >/dev/null 2>&1; then
        bun run seed 2>&1 || (cd backend && ../.venv/bin/python scripts/seed.py 2>&1 || ../.venv/Scripts/python.exe scripts/seed.py)
    else
        (cd backend && ../.venv/bin/python scripts/seed.py 2>&1 || ../.venv/Scripts/python.exe scripts/seed.py 2>&1 || python3 scripts/seed.py)
    fi
}

setup_env
check_mongo
setup_python

case "$MODE" in
    --start|--seed|"") seed_database ;;
    *) log_error "Unknown setup mode: $MODE"; exit 1 ;;
esac

log_info "Gavel setup complete"
