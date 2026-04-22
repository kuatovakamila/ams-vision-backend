.PHONY: help build up down logs shell test seed clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Show logs for all services
	docker-compose logs -f

logs-api: ## Show logs for FastAPI service
	docker-compose logs -f fastapi

logs-db: ## Show logs for PostgreSQL service
	docker-compose logs -f postgres

shell: ## Access FastAPI container shell
	docker-compose exec fastapi bash

shell-db: ## Access PostgreSQL shell
	docker-compose exec postgres psql -U ams_user -d ams_db

test: ## Run tests
	docker-compose exec fastapi python -m pytest test_main.py -v

seed: ## Seed database with sample data
	docker-compose exec fastapi python app/seed_db.py

migrate: ## Run database migrations
	docker-compose exec fastapi alembic upgrade head

migration: ## Create new migration (use: make migration MESSAGE="description")
	docker-compose exec fastapi alembic revision --autogenerate -m "$(MESSAGE)"

clean: ## Remove all containers, volumes, and images
	docker-compose down -v --rmi all

restart: ## Restart all services
	make down && make up

status: ## Show status of all services
	docker-compose ps

install: ## Install and start everything
	make build && make up && sleep 30 && make migrate && make seed

dev: ## Start development environment
	make up && make logs-api

# Development commands (for local development without Docker)
dev-install: ## Install Python dependencies locally
	pip install -r requirements.txt

dev-migrate: ## Run migrations locally
	alembic upgrade head

dev-migration: ## Create new migration locally
	alembic revision --autogenerate -m "$(MESSAGE)"

dev-seed: ## Seed database locally
	python seed_db.py

dev-run: ## Run FastAPI locally
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-test: ## Run tests locally
	python -m pytest test_main.py -v

dev-test2: ## Run tests locally
	python -m pytest test_main.py -v
