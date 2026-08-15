# PRODUCTION DEPLOYMENT CHECKLIST v1

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

Use this step-by-step release checklist prior to deploying any production update.

## Phase 1: Pre-Deployment Readiness
- [ ] **1. Backup Database**: Run `python scripts/backup_postgres.py` and verify backup file created in `data/backups/`.
- [ ] **2. Environment Configuration Audit**:
  - [ ] `APP_ENV=production`
  - [ ] `DEBUG=false`
  - [ ] Production database URL configured (non-default password).
  - [ ] Explicit `CORS_ORIGINS` specified (no wildcard `*`).
  - [ ] Explicit `TRUSTED_HOSTS` specified (no wildcard `*`).
  - [ ] Execute `python -m app.scripts.check_production_config --env production` (must return exit code 0).
- [ ] **3. Quality Gates Verification**:
  - [ ] Backend Pytest Suite: `pytest tests/ -v` (219+ PASS)
  - [ ] Validation Benchmark: `python -m app.scripts.run_validation_benchmark` (57/57 PASS)
  - [ ] Frontend Typecheck: `cd apps/web && npm run typecheck` (PASS)
  - [ ] Frontend Lint: `cd apps/web && npm run lint` (PASS)
  - [ ] Frontend Standalone Build: `cd apps/web && npm run build` (PASS)

## Phase 2: Build & Deployment Execution
- [ ] **4. Validate Docker Compose Syntax**: Execute `docker compose -f docker-compose.prod.yml config` (must return exit code 0).
- [ ] **5. Build Production Images**: Execute `docker compose -f docker-compose.prod.yml build`.
- [ ] **6. Run One-Shot Migration Job**: Start `postgres` and `migrate` services to apply schema updates (`alembic upgrade head`). Confirm exit code 0.
- [ ] **7. Launch Production Services**: Execute `docker compose -f docker-compose.prod.yml up -d`.

## Phase 3: Post-Deployment Smoke & Verification
- [ ] **8. Probe Liveness**: `curl -f http://localhost:8000/health/live` (must return HTTP 200).
- [ ] **9. Probe Readiness**: `curl -f http://localhost:8000/health/ready` (must return HTTP 200 with `database: healthy`, `storage: healthy`).
- [ ] **10. Execute Operational Smoke Tests**: Run `python scripts/smoke_production.py` (all endpoints must return 200 OK).
- [ ] **11. Verify Container Logs**: Check API logs for unhandled 500 exceptions or startup warnings (`docker logs carpet_api_prod`).
