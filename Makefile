# Docker Compose commands
up:
	docker compose up --build

down:
	docker compose down

down-v:
	docker compose down -v

logs:
	docker compose logs -f

logs-app:
	docker compose logs -f app

logs-celery:
	docker compose logs -f celery-worker celery-beat

logs-redis:
	docker compose logs -f redis

# Production commands
up-prod:
	docker compose -f docker-compose.prod.yml up --build -d

down-prod:
	docker compose -f docker-compose.prod.yml down

logs-prod:
	docker compose -f docker-compose.prod.yml logs -f

# Migration commands (Docker)
migrate:
	docker compose exec app alembic upgrade head

migrations-generate:
	docker compose exec app alembic revision --autogenerate -m "$(message)"

migrate-prod:
	docker compose -f docker-compose.prod.yml exec app alembic upgrade head

migrations-generate-prod:
	docker compose -f docker-compose.prod.yml exec app alembic revision --autogenerate -m "$(message)"

# Run FastAPI locally (for local development)
run-local:
	uvicorn src.main:app --reload --host localhost --port 8888

# Celery commands
celery-worker:
	celery -A src.celery_app worker --loglevel=info

celery-beat:
	celery -A src.celery_app beat --loglevel=info

celery-worker-beat:
	celery -A src.celery_app worker --beat --loglevel=info

# Cache commands (Docker)
init-cache:
	docker compose exec app python scripts/init_cache.py

init-cache-prod:
	docker compose -f docker-compose.prod.yml exec app python scripts/init_cache.py

# Check service status
status:
	docker compose ps

status-prod:
	docker compose -f docker-compose.prod.yml ps

# Redis commands
redis-start:
	brew services start redis

redis-stop:
	brew services stop redis

redis-status:
	brew services list | grep redis

# Database migration for cache tables
migrate-cache:
	alembic revision --autogenerate -m "add_notion_cache_tables"
	alembic upgrade head
