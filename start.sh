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
NC='\033[0m' # No Color

echo -e "${GREEN}[*] Threat Intelligence Platform - Başlatılıyor...${NC}"

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${RED}[!] python3 komutu bulunamadı.${NC}" >&2
  exit 1
fi

# Check Node.js (for frontend)
if ! command -v node >/dev/null 2>&1; then
  echo -e "${YELLOW}[!] Node.js bulunamadı. Frontend başlatılamayacak.${NC}" >&2
  FRONTEND_AVAILABLE=false
else
  FRONTEND_AVAILABLE=true
fi

# ==================== BACKEND SETUP ====================
echo -e "${GREEN}[*] Backend kurulumu...${NC}"

if [ ! -d "$BACKEND_DIR" ]; then
  echo -e "${RED}[!] backend dizini bulunamadı.${NC}" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "[*] Sanal ortam oluşturuluyor: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "[*] Python paketleri kontrol ediliyor..."
pip install --upgrade pip >/dev/null
pip install -r "$REQUIREMENTS_FILE" >/dev/null 2>&1 || {
  echo -e "${YELLOW}[!] Bazı paketler kurulamadı, devam ediliyor...${NC}"
}

if [ ! -f "$ENV_FILE" ]; then
  echo "[*] $ENV_FILE bulunamadı. .env.example dosyasından oluşturuluyor..."
  if [ -f "$BACKEND_DIR/.env.example" ]; then
    cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
    echo "[*] .env dosyası oluşturuldu. Gerekirse düzenleyin."
  else
    echo "[*] .env.example bulunamadı, varsayılan ayarlar kullanılacak."
    echo "DATABASE_URL=sqlite:///./threat_intel.db" > "$ENV_FILE"
  fi
fi

# Load environment variables
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# ==================== FRONTEND SETUP ====================
if [ "$FRONTEND_AVAILABLE" = true ]; then
  echo -e "${GREEN}[*] Frontend kurulumu...${NC}"
  
  if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${YELLOW}[!] frontend dizini bulunamadı. Frontend atlanıyor.${NC}" >&2
    FRONTEND_AVAILABLE=false
  else
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
      echo "[*] npm paketleri kuruluyor (bu biraz zaman alabilir)..."
      npm install
    else
      echo "[*] npm paketleri zaten kurulu."
    fi
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
      echo "[*] Frontend .env dosyası oluşturuluyor..."
      if [ -f "env.example" ]; then
        cp env.example .env
      else
        echo "VITE_API_BASE_URL=http://127.0.0.1:8000" > .env
      fi
    fi
  fi
fi

# ==================== CLEANUP OLD SERVICES ====================
echo -e "${YELLOW}[*] Eski servisler temizleniyor...${NC}"

# Kill existing backend processes
if lsof -ti:8000 >/dev/null 2>&1; then
  echo "[*] Port 8000'de çalışan process(ler) durduruluyor..."
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
  sleep 1
fi

# Kill existing frontend processes
if [ "$FRONTEND_AVAILABLE" = true ] && lsof -ti:5173 >/dev/null 2>&1; then
  echo "[*] Port 5173'te çalışan process(ler) durduruluyor..."
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
echo -e "${GREEN}[*] Temizlik tamamlandı${NC}"

# ==================== START SERVICES ====================
echo -e "${GREEN}[*] Servisler başlatılıyor...${NC}"

# Function to cleanup on exit
cleanup() {
  echo -e "\n${YELLOW}[*] Servisler durduruluyor...${NC}"
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
  exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "${GREEN}[*] Backend başlatılıyor (http://127.0.0.1:8000)...${NC}"
cd "$BACKEND_DIR"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 2

# Start Frontend
if [ "$FRONTEND_AVAILABLE" = true ]; then
  echo -e "${GREEN}[*] Frontend başlatılıyor (http://localhost:5173)...${NC}"
  cd "$FRONTEND_DIR"
  npm run dev > /tmp/frontend.log 2>&1 &
  FRONTEND_PID=$!
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}[✓] Servisler başlatıldı!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backend:${NC}  http://127.0.0.1:8000"
echo -e "${GREEN}API Docs:${NC} http://127.0.0.1:8000/docs"
if [ "$FRONTEND_AVAILABLE" = true ]; then
  echo -e "${GREEN}Frontend:${NC} http://localhost:5173"
fi
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}[*] Log dosyaları:${NC}"
echo "  Backend:  tail -f /tmp/backend.log"
if [ "$FRONTEND_AVAILABLE" = true ]; then
  echo "  Frontend: tail -f /tmp/frontend.log"
fi
echo ""
echo -e "${YELLOW}[*] Durdurmak için Ctrl+C tuşlarına basın${NC}"
echo ""

# Wait for processes
wait $BACKEND_PID
if [ "$FRONTEND_AVAILABLE" = true ]; then
  wait $FRONTEND_PID
fi
