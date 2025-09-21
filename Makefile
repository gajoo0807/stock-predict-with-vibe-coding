# Makefile for managing the project

.PHONY: up down logs test fmt lint

up:
	docker-compose -f infra/docker-compose.yml up -d --build

down:
	docker-compose -f infra/docker-compose.yml down

logs:
	docker-compose -f infra/docker-compose.yml logs -f

test:
	poetry run pytest services/market_data
	poetry run pytest services/rag
	poetry run pytest services/llm
	poetry run pytest gateway

fmt:
	black .
	isort .

lint:
	ruff .
