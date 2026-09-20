.PHONY: up down logs test lint seed migrate reset

# Start the full Docker Compose stack
up:
	docker compose up --build -d

# Stop the stack
down:
	docker compose down -v

# View logs for all services
logs:
	docker compose logs -f

# Run tests
test:
	docker compose exec api pytest tests/
	docker compose exec inference-worker pytest tests/

# Run linting
lint:
	docker compose exec api flake8 app/ tests/
	docker compose exec inference-worker flake8 app/ tests/
	docker compose exec frontend npm run lint

# Seed the database and watchlists
seed:
	docker compose exec inference-worker python scripts/seed_watchlist.py

# Run database migrations
migrate:
	docker compose exec api alembic upgrade head

# Completely wipe containers and volumes, then restart
reset: down up
