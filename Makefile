.PHONY: up down test lint check backend-test frontend-lint frontend-typecheck frontend-build

up:
	docker compose up -d --build

down:
	docker compose down

backend-test:
	cd apps/api && python -m pytest tests/ -v

frontend-lint:
	cd apps/web && npm run lint

frontend-typecheck:
	cd apps/web && npm run typecheck

frontend-build:
	cd apps/web && npm run build

test: backend-test

lint: frontend-lint

check: backend-test frontend-lint frontend-typecheck frontend-build
