#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

echo -e "${BLUE}Threat Intelligence Platform - Docker Startup${NC}\n"

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

if docker compose version > /dev/null 2>&1; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

gen_secret() { openssl rand -base64 48 | tr -d '\n/+=' | cut -c1-48; }

touch .env
chmod 600 .env

# Values that ship in example files are treated as missing.
is_weak() {
    case "$1" in
        ""|your-*|change-*|changeme*) return 0 ;;
    esac
    [ "${#1}" -lt 32 ]
}

ensure_secret() {
    local key="$1" current
    current="$(grep -E "^${key}=" .env | tail -1 | cut -d= -f2- || true)"
    if is_weak "$current"; then
        [ -f .env.bak ] || cp .env .env.bak
        grep -vE "^${key}=" .env > .env.tmp || true
        mv .env.tmp .env
        echo "${key}=$(gen_secret)" >> .env
        echo -e "${YELLOW}Generated a new ${key} in .env${NC}"
    fi
}

ensure_secret SECRET_KEY
ensure_secret ENCRYPTION_KEY
ensure_secret REDIS_PASSWORD
chmod 600 .env

echo -e "${GREEN}Building and starting containers...${NC}\n"
$COMPOSE up -d --build

echo
echo -e "${GREEN}Services started${NC}"
echo -e "  Frontend:  http://localhost:${FRONTEND_PORT:-4765}"
echo -e "  API docs:  http://127.0.0.1:8777/docs (localhost only)"
echo
echo -e "${YELLOW}First start:${NC} an 'admin' account is created. Its password is DEFAULT_ADMIN_PASSWORD"
echo -e "from .env, or a random one printed once in the backend log:"
echo -e "  $COMPOSE logs backend | grep 'Initial admin'"
echo -e "Set SEED_DEFAULT_USERS=true in .env to create demo users (admin/admin123 ...) - lab use only."
