# Threat Intelligence Platform

A web application for querying, analyzing, and reporting on IOC (Indicators of Compromise) using open-source threat intelligence APIs.

## 🚀 Quick Start

### Requirements

- **Python 3.12+** (for Backend)
- **Node.js 20+ and npm 10+** (for Frontend - optional)
- **Docker & Docker Compose** (for containerized deployment - optional)

### Option 1: Docker Deployment (Recommended)

```bash
# Start all services with one command
./docker-start.sh

# Or directly
docker-compose up -d
```

This will start:
- Redis (for caching)
- Backend API (FastAPI)
- Frontend (React + Nginx)

**Access URLs:**
- Frontend: http://localhost
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Option 2: Local Development

#### Start with Script

```bash
./start.sh
```

This script:
- ✅ Automatically sets up and starts the backend
- ✅ Sets up and starts the frontend (if Node.js is installed)
- ✅ Creates necessary `.env` files
- ✅ Runs both services in parallel

#### Manual Setup

##### Backend Only

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

##### Frontend (Node.js required)

```bash
# Install Node.js (Mac - with Homebrew)
brew install node

# Install Node.js (Linux)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install and start frontend
cd frontend
npm install
npm run dev
```

## 📁 Project Structure

```
pentest_report_tool/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── core/     # Config, security, dependencies
│   │   ├── db/       # Database models and migrations
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   └── services/ # Business logic
│   └── requirements.txt
├── frontend/         # React + Vite frontend
│   ├── src/
│   │   ├── features/ # Feature modules
│   │   ├── components/ # UI components
│   │   └── lib/      # API client
│   └── package.json
├── docker/           # Docker configuration files
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── docker-compose.yml  # Docker Compose configuration
├── docker-start.sh     # Docker startup script
└── start.sh            # Local development startup script
```

## 🌐 Access URLs

### Local Development

After backend starts:
- **Backend API**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/api/v1/health

After frontend starts:
- **Frontend**: http://localhost:5173

### Docker Deployment

- **Frontend**: http://localhost:4765
- **Backend API**: http://localhost:8777
- **API Documentation**: http://localhost:8777/docs

## 🔧 Configuration

### Backend (.env)

Edit `backend/.env` file:

```bash
DATABASE_URL=sqlite:///./threat_intel.db
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-32-byte-encryption-key!!
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
```

### Frontend (.env)

Edit `frontend/.env` file:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Docker (.env)

For Docker deployment, copy `.env.example` to `.env` in the root directory:

```bash
cp .env.example .env
# Edit .env and change SECRET_KEY and ENCRYPTION_KEY
```

## 📚 Features

### ✅ Completed Modules

- **Authentication**: JWT-based user login and registration
- **IOC Query**: IP, domain, URL, hash querying with multiple threat intelligence sources
- **Dashboard**: Statistics and metrics with charts
- **CVE Database**: NIST NVD integration with search and filtering
- **Watchlist**: Asset monitoring and alert system
- **Reports**: Generate reports from IOC queries (PDF, HTML, JSON, CSV)
- **API Key Management**: Encrypted API key management
- **API Source Management**: Add custom API sources dynamically
- **Alert System**: Alert notifications for watchlist items
- **Redis Caching**: High-performance caching for IOC and CVE queries
- **Background Jobs**: Automated watchlist monitoring

### 🔄 Development Status

- Most core features are complete
- Frontend UI fully implemented
- Protected routes implemented
- PDF export available
- Background task system implemented

## 🛠️ Development

### Backend Testing

```bash
cd backend
source .venv/bin/activate
pytest
```

### Frontend Testing

```bash
cd frontend
npm test  # When tests are added
```

## 📝 Notes

- SQLite is used in development environment
- PostgreSQL is recommended for production
- API keys are encrypted with AES-256
- JWT tokens are valid for 30 minutes
- Redis cache is enabled by default in Docker

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is open source.
