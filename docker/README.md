# Threat Intelligence Platform - Docker Deployment

This directory contains all files needed to easily deploy the Threat Intelligence Platform using Docker.

## 🚀 Quick Start

### Start with Single Command

```bash
docker-compose up -d
```

This command will start:
- **Redis** (for caching)
- **Backend API** (FastAPI)
- **Frontend** (React + Nginx)

### Stop Services

```bash
docker-compose down
```

### Stop Services and Remove All Data

```bash
docker-compose down -v
```

---

## 📋 Requirements

- Docker 20.10+
- Docker Compose 2.0+

---

## 🔧 Configuration

### Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and especially change these values:
   - `SECRET_KEY`: A strong secret key
   - `ENCRYPTION_KEY`: A 32-character encryption key
   - `DATABASE_URL`: Change if using PostgreSQL

### Using PostgreSQL (Optional)

By default, SQLite is used. To use PostgreSQL:

1. Configure PostgreSQL settings in the `.env` file:
   ```env
   DATABASE_URL=postgresql://threat_intel:threat_intel_password@postgres:5432/threat_intel
   ```

2. Start with PostgreSQL profile:
   ```bash
   docker-compose --profile postgres up -d
   ```

---

## 🌐 Access URLs

After services start:

- **Frontend (Main Application)**: http://localhost:4765
- **Backend API**: http://localhost:8777
- **API Documentation**: http://localhost:8777/docs
- **Health Check**: http://localhost:4765/api/v1/health

---

## 📊 Service Status Check

### View status of all services:
```bash
docker-compose ps
```

### View logs:
```bash
# All logs
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend

# Redis only
docker-compose logs -f redis
```

### Health check:
```bash
curl http://localhost/api/v1/health
```

---

## 🔨 Development Mode

For development to see code changes in real-time:

### For Backend:
Add a volume to the backend service in `docker-compose.yml`:
```yaml
volumes:
  - ../backend:/app
```

### For Frontend:
Use development build (with hot reload):
```yaml
# In frontend service
command: npm run dev -- --host 0.0.0.0
```

---

## 📦 Data Backup

### Database Backup (SQLite):
```bash
docker-compose exec backend cp /app/data/threat_intel.db /app/data/threat_intel.db.backup
```

### Redis Backup:
```bash
docker-compose exec redis redis-cli SAVE
docker-compose exec redis cp /data/dump.rdb /data/dump.rdb.backup
```

### Backup All Volumes:
```bash
docker run --rm -v threat-intel_backend_data:/data -v $(pwd):/backup alpine tar czf /backup/backend_data_backup.tar.gz /data
```

---

## 🐛 Troubleshooting

### Backend not starting:
1. Check logs: `docker-compose logs backend`
2. Make sure port 8000 is available
3. Ensure `.env` file is properly configured

### Frontend not starting:
1. Check logs: `docker-compose logs frontend`
2. Make sure port 80 is available
3. Ensure backend is running properly

### Redis connection error:
1. Check if Redis service is running: `docker-compose ps redis`
2. Check Redis logs: `docker-compose logs redis`

### Port conflict:
If ports are in use, change ports in `docker-compose.yml`:
```yaml
ports:
  - "8777:8000"  # For backend
  - "8081:80"    # For frontend
```

---

## 🔄 Updating

### Code updates:
```bash
# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Start services
docker-compose up -d
```

### Rebuild only a specific service:
```bash
docker-compose build backend
docker-compose up -d backend
```

---

## 📝 Notes

- Backend automatically creates database tables on first start
- Redis cache is automatically enabled
- Frontend is served with Nginx and proxies to backend API
- All data is stored in Docker volumes

---

## 🛠️ Advanced Usage

### Production Deployment:
1. Configure production settings in `.env` file
2. Add nginx reverse proxy for HTTPS
3. Configure SSL certificates
4. Add resource limits (CPU, memory)

### Monitoring:
Monitor resource usage with Docker stats:
```bash
docker stats
```

### Database Migrations:
```bash
docker-compose exec backend alembic upgrade head
```

---

## 📞 Support

If you encounter issues:
1. Check logs
2. Check service statuses
3. Report issues on GitHub Issues
