# Notion Stats Backend

FastAPI backend service for fetching and caching Notion workspace statistics.

## 🚀 Quick Start with Docker

The **easiest way** to run this project:

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Edit .env with your Notion credentials
nano .env

# 3. Start everything!
docker compose up --build
```

That's it! 🎉

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Cache updates**: Automatically every 30 minutes

## 📚 Documentation

- **[DOCKER_GUIDE.md](./DOCKER_GUIDE.md)** - Complete Docker setup and commands
- **[CACHE_SYSTEM_GUIDE.md](./CACHE_SYSTEM_GUIDE.md)** - How the caching system works
- **[ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)** - System architecture overview
- **[IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md)** - Implementation checklist

## 🐳 Docker Services

Your stack includes:
- ✅ PostgreSQL - Database
- ✅ Redis - Message broker
- ✅ FastAPI - API server
- ✅ Celery Worker - Background tasks
- ✅ Celery Beat - Task scheduler
- ✅ Migrations - Auto-runs Alembic

## 🔧 Common Commands

```bash
# Start all services
make up

# View logs
make logs

# Stop everything
make down

# Check service status
make status

# Generate migration
make migrations-generate message="add new field"

# Initialize cache manually
make init-cache
```

See [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) for complete command reference.

## ⚡ Performance

- **Without Cache**: 3-4 minutes per request (Notion API)
- **With Cache**: 50-100ms per request (PostgreSQL)
- **Speed Improvement**: ~2400x faster! 🚀

## 🏗️ Architecture

```
Frontend Request
    ↓
FastAPI (reads from PostgreSQL cache) → 50ms response!
    ↑
    │ Updated every 30 minutes by:
    │
Celery Beat (scheduler)
    ↓
Celery Worker (fetches from Notion API)
    ↓
PostgreSQL (saves cache)
```

## 📋 Environment Variables

Required variables (copy from `.env.example`):

- `NOTION_API_KEY` - Your Notion integration key
- `NOTION_DATABASE_ID` - Your Notion database ID
- `DB_PASSWORD` - PostgreSQL password
- `SECRET_KEY` - JWT secret key

## 🔒 Production Deployment

```bash
# Use production compose file
make up-prod

# View production logs
make logs-prod
```

Production optimizations:
- 4 uvicorn workers
- Minimal logging
- No volume mounts (no hot reload)
- Redis memory limits
- Auto-restarts

## 🆘 Troubleshooting

**Services won't start?**
```bash
make down-v  # Clean slate
make up      # Restart
```

**Migrations failing?**
```bash
docker compose logs migrations
```

**Cache not updating?**
```bash
make logs-celery  # Check Celery logs
make init-cache   # Force update
```

See [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) for detailed troubleshooting.

## 🛠️ Development

### Local Development (without Docker)

If you prefer running locally:

1. Install dependencies:
```bash
pip install -e .
```

2. Start PostgreSQL and Redis manually

3. Run migrations:
```bash
alembic upgrade head
```

4. Start services in separate terminals:
```bash
# Terminal 1: API
uvicorn src.main:app --reload

# Terminal 2: Celery Worker
celery -A src.celery_app worker --loglevel=info

# Terminal 3: Celery Beat
celery -A src.celery_app beat --loglevel=info
```

### Project Structure

```
.
├── src/
│   ├── api/v1/          # API endpoints
│   ├── services/        # Business logic (CachedNotionService)
│   ├── repositories/    # Database access (CacheRepository)
│   ├── schemas/         # SQLAlchemy models & Pydantic schemas
│   ├── tasks/           # Celery background tasks
│   ├── celery_app.py    # Celery configuration
│   └── main.py          # FastAPI application
├── alembic/             # Database migrations
├── scripts/             # Utility scripts
├── docker-compose.yml   # Docker services (dev)
├── docker-compose.prod.yml  # Docker services (prod)
└── Dockerfile           # Container image
```

## 📊 API Endpoints

All endpoints require authentication (JWT token).

### Projects
- `GET /api/v1/notion/projects` - Get all projects
- `GET /api/v1/notion/projects/health/{status}` - Filter by health status
- `GET /api/v1/notion/projects/statistics` - Project statistics

### Tasks
- `GET /api/v1/notion/tasks` - Get all tasks
- `POST /api/v1/notion/tasks/filter` - Filter tasks

### Todos
- `GET /api/v1/notion/todos` - Get all todos
- `GET /api/v1/notion/todos/member/{name}` - Todos by member
- `GET /api/v1/notion/todos/overdue` - Overdue todos
- `GET /api/v1/notion/todos/statistics` - Todo statistics
- `GET /api/v1/notion/todos/active` - Active todos only

### Auth
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=src
```

## 📝 License

[Your License Here]

## 🤝 Contributing

[Your Contributing Guidelines]

---

Made with ❤️ for faster Notion data access
