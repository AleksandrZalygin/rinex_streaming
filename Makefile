.PHONY: help build up down restart logs clean status shell-scheduler shell-api check-docker

# Detect Docker Compose version
# Try v2 first (docker compose), then fallback to v1 (docker-compose)
DOCKER_COMPOSE := $(shell docker compose version > /dev/null 2>&1 && echo "docker compose" || echo "docker-compose")
COMPOSE_FILE := $(shell [ "$(DOCKER_COMPOSE)" = "docker compose" ] && echo "compose.yaml" || echo "docker-compose.yml")

help:
	@echo "RINEX Streaming - Docker Commands"
	@echo "=================================="
	@echo ""
	@echo "Current Docker Compose: $(DOCKER_COMPOSE)"
	@echo "Using config file: $(COMPOSE_FILE)"
	@echo ""
	@echo "Docker commands:"
	@echo "  make check-docker   - Check Docker Compose version"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - Show logs from all services"
	@echo "  make logs-scheduler - Show scheduler logs"
	@echo "  make logs-api       - Show API logs"
	@echo "  make logs-rabbitmq  - Show RabbitMQ logs"
	@echo "  make status         - Show status of services"
	@echo "  make shell-scheduler - Open shell in scheduler container"
	@echo "  make shell-api      - Open shell in API container"
	@echo "  make clean          - Stop and remove all containers, networks, volumes"
	@echo ""
	@echo "Manual run (without Docker):"
	@echo "  make run-api        - Run API server manually"
	@echo "  make run-scheduler  - Run scheduler manually"
	@echo ""
	@echo "Alternative commands (force specific version):"
	@echo "  make up-v1          - Use docker-compose (v1)"
	@echo "  make up-v2          - Use docker compose (v2)"

check-docker:
	@echo "Checking Docker Compose installation..."
	@echo ""
	@if command -v docker > /dev/null 2>&1; then \
		echo "✓ Docker is installed"; \
		docker --version; \
	else \
		echo "✗ Docker is not installed"; \
		exit 1; \
	fi
	@echo ""
	@if docker compose version > /dev/null 2>&1; then \
		echo "✓ Docker Compose v2 is available (recommended)"; \
		docker compose version; \
		echo "  Using: docker compose -f compose.yaml"; \
	elif command -v docker-compose > /dev/null 2>&1; then \
		echo "✓ Docker Compose v1 is available (legacy)"; \
		docker-compose --version; \
		echo "  Using: docker-compose -f docker-compose.yml"; \
	else \
		echo "✗ Docker Compose is not installed"; \
		exit 1; \
	fi
	@echo ""
	@echo "Current selection: $(DOCKER_COMPOSE)"
	@echo "Config file: $(COMPOSE_FILE)"

build:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) build

up:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d
	@echo ""
	@echo "Services started. Check status with 'make status'"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "RabbitMQ UI: http://localhost:15672 (guest/guest)"

down:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down

restart:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) restart

logs:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f

logs-scheduler:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f scheduler

logs-api:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f api

logs-rabbitmq:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f rabbitmq

status:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) ps

shell-scheduler:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec scheduler bash

shell-api:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) exec api bash

clean:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down -v --rmi all
	@echo "All containers, networks, images and volumes removed"

# Force use of specific version
up-v1:
	docker-compose -f docker-compose.yml up -d
	@echo ""
	@echo "Started with docker-compose v1"

up-v2:
	docker compose -f compose.yaml up -d
	@echo ""
	@echo "Started with docker compose v2"

build-v1:
	docker-compose -f docker-compose.yml build

build-v2:
	docker compose -f compose.yaml build

down-v1:
	docker-compose -f docker-compose.yml down

down-v2:
	docker compose -f compose.yaml down

# Manual run commands (without Docker)
run-api:
	cd src/rnx_streamer && uvicorn API_server:app --host 0.0.0.0 --port 8000

run-scheduler:
	cd src/rnx_streamer && python3 scheduler.py
