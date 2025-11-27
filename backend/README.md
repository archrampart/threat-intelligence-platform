# Threat Intelligence Backend

FastAPI-based threat intelligence platform backend.

## Installation

### Requirements
- Python 3.12+
- pip

### Quick Start

```bash
# From project root directory
./start.sh
```

This script:
1. Creates Python virtual environment (if it doesn't exist)
2. Installs required packages
3. Creates `.env` file (if it doesn't exist)
4. Starts the backend

### Manual Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install packages
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env file if needed

# Start backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Configuration

### Environment Variables (.env)

```bash
# Application Settings
APP_NAME="Threat Intelligence Platform API"
APP_VERSION="0.1.0"
ENVIRONMENT="development"
API_V1_STR="/api/v1"
DOCS_URL="/docs"

# Database (SQLite - for development)
DATABASE_URL="sqlite:///./threat_intel.db"

# PostgreSQL (for production)
# DATABASE_URL="postgresql://user:password@localhost/dbname"

# Redis Cache
REDIS_ENABLED=true
REDIS_URL="redis://localhost:6379/0"

# JWT Authentication
SECRET_KEY="your-secret-key-change-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption
ENCRYPTION_KEY="your-32-byte-encryption-key-change-in-production!!"

# API Keys (optional)
VIRUSTOTAL_API_KEY=""
ABUSEIPDB_API_KEY=""
OTX_API_KEY=""
```

## API Endpoints

After backend starts:
- API Docs: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/api/v1/health

### Main Endpoints

- `POST /api/v1/auth/login` - Login
- `GET /api/v1/dashboard` - Dashboard data
- `POST /api/v1/ioc/query` - IOC query
- `GET /api/v1/ioc/history` - IOC query history
- `GET /api/v1/cves/search` - CVE search
- `GET /api/v1/watchlists` - Watchlist list
- `GET /api/v1/reports` - Report list

## Notes

- **Development**: SQLite is used, `psycopg2-binary` is not required
- **Production**: PostgreSQL is used, `psycopg2-binary` should be added to requirements.txt
- Database tables are automatically created on first run
- Predefined API sources are automatically seeded
- Redis cache is enabled by default (if Redis is available)
