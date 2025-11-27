#!/bin/bash
# Threat Intelligence Platform - Docker Startup Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Threat Intelligence Platform${NC}"
echo -e "${BLUE}  Starting Docker Services...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Docker check
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

# Docker Compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# .env file check
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Please edit .env file and change SECRET_KEY and ENCRYPTION_KEY values!${NC}"
        echo ""
    else
        echo -e "${YELLOW}⚠️  .env.example file not found. Continuing with default values.${NC}"
        echo ""
    fi
fi

# Clean up old containers
echo -e "${YELLOW}[*] Checking for old containers...${NC}"
$DOCKER_COMPOSE down 2>/dev/null || true

# Build and start
echo -e "${GREEN}[*] Building Docker images...${NC}"
$DOCKER_COMPOSE build

echo -e "${GREEN}[*] Starting services...${NC}"
$DOCKER_COMPOSE up -d

# Wait for services to be ready
echo -e "${YELLOW}[*] Waiting for services to be ready...${NC}"
sleep 5

# Health check
echo -e "${YELLOW}[*] Performing health check...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:4765/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is healthy!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}   Attempt $RETRY_COUNT/$MAX_RETRIES...${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}⚠️  Backend is not ready yet. Check logs: $DOCKER_COMPOSE logs backend${NC}"
fi

# Service statuses
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Services started!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
$DOCKER_COMPOSE ps
echo ""

# URL information
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🌐 Access URLs:${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Frontend:     ${GREEN}http://localhost:4765${NC}"
echo -e "Backend API:  ${GREEN}http://localhost:8777${NC}"
echo -e "API Docs:     ${GREEN}http://localhost:8777/docs${NC}"
echo -e "Health:       ${GREEN}http://localhost:4765/api/v1/health${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Usage information
echo -e "${YELLOW}📝 Usage:${NC}"
echo -e "  View logs:            ${BLUE}$DOCKER_COMPOSE logs -f${NC}"
echo -e "  Stop services:        ${BLUE}$DOCKER_COMPOSE down${NC}"
echo -e "  Service status:       ${BLUE}$DOCKER_COMPOSE ps${NC}"
echo -e "  Restart services:     ${BLUE}$DOCKER_COMPOSE restart${NC}"
echo ""

# Default user credentials
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🔐 Default Login Credentials:${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}Admin User:${NC}"
echo -e "  Username: ${GREEN}admin${NC}"
echo -e "  Password: ${GREEN}admin123${NC}"
echo -e "  Role:     ${GREEN}ADMIN${NC}"
echo ""
echo -e "${YELLOW}Analyst User:${NC}"
echo -e "  Username: ${GREEN}analyst${NC}"
echo -e "  Password: ${GREEN}analyst123${NC}"
echo -e "  Role:     ${GREEN}ANALYST${NC}"
echo ""
echo -e "${YELLOW}Viewer User:${NC}"
echo -e "  Username: ${GREEN}viewer${NC}"
echo -e "  Password: ${GREEN}viewer123${NC}"
echo -e "  Role:     ${GREEN}VIEWER${NC}"
echo ""
echo -e "${YELLOW}⚠️  Note:${NC} These credentials are for development only!"
echo -e "${YELLOW}   ${NC} Change default passwords in production."
echo ""
