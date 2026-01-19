#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Threat Intelligence Platform - Docker Startup         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if .env file exists, create from example if not
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Please edit .env file to set your SECRET_KEY and ENCRYPTION_KEY${NC}"
    else
        echo -e "${YELLOW}Creating default .env file...${NC}"
        cat > .env << EOF
SECRET_KEY=change-this-to-a-secure-random-string
ENCRYPTION_KEY=your-32-byte-encryption-key!!
EOF
    fi
fi

# Build and start containers
echo -e "${GREEN}Building and starting Docker containers...${NC}"
echo

docker-compose up -d --build

echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Services Started!                       ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Frontend:      http://localhost:4765                      ║${NC}"
echo -e "${GREEN}║  Backend API:   http://localhost:8777                      ║${NC}"
echo -e "${GREEN}║  API Docs:      http://localhost:8777/docs                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${YELLOW}Default Credentials:${NC}"
echo -e "  Admin:   admin@example.com / admin123"
echo -e "  Analyst: analyst@example.com / analyst123"
echo -e "  Viewer:  viewer@example.com / viewer123"
echo
echo -e "${BLUE}Use 'docker-compose logs -f' to view logs${NC}"
echo -e "${BLUE}Use 'docker-compose down' to stop services${NC}"
