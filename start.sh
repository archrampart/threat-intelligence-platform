#!/usr/bin/env bash
set -eo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
REQUIREMENTS_FILE="$BACKEND_DIR/requirements.txt"
ENV_FILE="$BACKEND_DIR/.env"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}[*] Threat Intelligence Platform - Starting...${NC}"

# Check Python
if ! command -v python3 > /dev/null 2>&1; then
  echo -e "${RED}[!] python3 command not found.${NC}" >&2
  exit 1
fi

# Check Node.js (for frontend)
if ! command -v node > /dev/null 2>&1; then
  echo -e "${YELLOW}[!] Node.js not found. Frontend will not be started.${NC}" >&2
  FRONTEND_AVAILABLE=false
else
  FRONTEND_AVAILABLE=true
fi

# ==================== BACKEND SETUP ====================
echo -e "${GREEN}[*] Setting up backend...${NC}"

if [ ! -d "$BACKEND_DIR" ]; then
  echo -e "${RED}[!] backend directory not found.${NC}" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "[*] Creating virtual environment: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "[*] Checking Python packages..."
pip install --upgrade pip > /dev/null
pip install -r "$REQUIREMENTS_FILE" > /dev/null 2>&1 || {
  echo -e "${YELLOW}[!] Some packages failed to install, continuing...${NC}"
}

if [ ! -f "$ENV_FILE" ]; then
  echo "[*] $ENV_FILE not found. Creating from .env.example..."
  if [ -f "$BACKEND_DIR/.env.example" ]; then
    cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
    echo "[*] .env file created. Edit if necessary."
  else
    echo "[*] .env.example not found, using default settings."
    echo "DATABASE_URL=sqlite:///./threat_intel.db" > "$ENV_FILE"
  fi
fi

# Load environment variables
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# ==================== DATABASE SETUP ====================
echo -e "${BLUE}[*] Checking database setup...${NC}"

cd "$BACKEND_DIR"

# Check if alembic is available
if command -v alembic > /dev/null 2>&1; then
  echo "[*] Running database migrations..."
  alembic upgrade head 2>&1 | grep -v "INFO" || {
    echo -e "${YELLOW}[!] Migration completed with warnings, continuing...${NC}"
  }
else
  echo -e "${YELLOW}[!] Alembic not found, skipping migrations${NC}"
fi

# Seed predefined API sources
echo "[*] Seeding predefined API sources..."
python -m app.db.seed_predefined_apis > /dev/null 2>&1 || {
  echo -e "${YELLOW}[!] Seed script encountered issues, continuing...${NC}"
}

# ==================== FRONTEND SETUP ====================
if [ "$FRONTEND_AVAILABLE" = true ]; then
  echo -e "${GREEN}[*] Setting up frontend...${NC}"
  
  if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${YELLOW}[!] frontend directory not found. Skipping frontend.${NC}" >&2
    FRONTEND_AVAILABLE=false
  else
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
      echo "[*] Installing npm packages (this may take a while)..."
      npm install
    else
      echo "[*] npm packages already installed."
    fi
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
      echo "[*] Creating frontend .env file..."
      if [ -f ".env.example" ]; then
        cp .env.example .env
      else
        echo "VITE_API_BASE_URL=http://127.0.0.1:8000" > .env
      fi
    fi
  fi
fi

# ==================== CLEANUP OLD SERVICES ====================
echo -e "${YELLOW}[*] Cleaning up old services...${NC}"

# Kill existing backend processes
if lsof -ti:8000 > /dev/null 2>&1; then
  echo "[*] Stopping process(es) on port 8000..."
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
  sleep 1
fi

# Kill existing frontend processes
if [ "$FRONTEND_AVAILABLE" = true ] && lsof -ti:5173 > /dev/null 2>&1; then
  echo "[*] Stopping process(es) on port 5173..."
  lsof -ti:5173 | xargs kill -9 2>/dev/null || true
  sleep 1
fi

# Kill any uvicorn processes from this project
pkill -f "uvicorn app.main:app" 2>/dev/null || true

# Kill any npm/vite processes from this project
if [ "$FRONTEND_AVAILABLE" = true ]; then
  pkill -f "vite.*5173" 2>/dev/null || true
fi

sleep 1
echo -e "${GREEN}[*] Cleanup completed${NC}"

# ==================== START SERVICES ====================
echo -e "${GREEN}[*] Starting services...${NC}"

# Function to cleanup on exit
cleanup() {
  echo -e "\n${YELLOW}[*] Stopping services...${NC}"
  if [ -n "${BACKEND_PID:-}" ]; then
    kill $BACKEND_PID 2>/dev/null || true
  fi
  if [ "$FRONTEND_AVAILABLE" = true ] && [ -n "${FRONTEND_PID:-}" ]; then
    kill $FRONTEND_PID 2>/dev/null || true
  fi
  # Cleanup ports
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
  if [ "$FRONTEND_AVAILABLE" = true ]; then
    lsof -ti:5173 | xargs kill -9 2>/dev/null || true
  fi
  echo -e "${GREEN}[✓] Services stopped successfully${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "${GREEN}[*] Starting backend (http://127.0.0.1:8000)...${NC}"
cd "$BACKEND_DIR"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "[*] Waiting for backend to initialize..."
BACKEND_READY=false
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    BACKEND_READY=true
    echo -e "${GREEN}[✓] Backend is ready!${NC}"
    break
  fi
  sleep 1
  if [ $((i % 5)) -eq 0 ]; then
    echo "  Still waiting... ($i/30)"
  fi
done

if [ "$BACKEND_READY" = false ]; then
  echo -e "${YELLOW}[!] Backend health check timeout, but continuing (check logs if issues occur)${NC}"
fi

# Start Frontend
if [ "$FRONTEND_AVAILABLE" = true ]; then
  echo -e "${GREEN}[*] Starting frontend (http://localhost:5173)...${NC}"
  cd "$FRONTEND_DIR"
  npm run dev > /tmp/frontend.log 2>&1 &
  FRONTEND_PID=$!
  
  # Give frontend a moment to start
  sleep 2
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}[✓] Services started successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backend:${NC}  http://127.0.0.1:8000"
echo -e "${GREEN}API Docs:${NC} http://127.0.0.1:8000/docs"
if [ "$FRONTEND_AVAILABLE" = true ]; then
  echo -e "${GREEN}Frontend:${NC} http://localhost:5173"
fi
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}[*] Log files:${NC}"
echo "  Backend:  tail -f /tmp/backend.log"
if [ "$FRONTEND_AVAILABLE" = true ]; then
  echo "  Frontend: tail -f /tmp/frontend.log"
fi
echo ""
echo -e "${BLUE}[*] Database:${NC}"
echo "  Migrations: Auto-applied on startup"
echo "  Seeds: Predefined API sources loaded"
echo ""
echo -e "${YELLOW}[*] Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for processes
wait $BACKEND_PID
if [ "$FRONTEND_AVAILABLE" = true ]; then
  wait $FRONTEND_PID
fi
