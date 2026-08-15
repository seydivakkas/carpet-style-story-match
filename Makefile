.PHONY: up down test lint check backend-test frontend-lint frontend-typecheck frontend-build prod-build prod-config-check prod-smoke

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

prod-build:
	docker compose -f docker-compose.prod.yml build

prod-config-check:
	cd apps/api && python -m app.scripts.check_production_config --env production

prod-smoke:
	python scripts/smoke_production.py

test: backend-test

lint: frontend-lint

check: backend-test frontend-lint frontend-typecheck frontend-build
