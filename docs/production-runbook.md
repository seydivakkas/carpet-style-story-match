# PRODUCTION RUNBOOK & OPERATIONAL PROCEDURES v1

```
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
```

## 1. System Architecture Overview

The **Carpet Style & Story Match v1** platform consists of 4 primary containerized production services:

- **PostgreSQL Database (`postgres`)**: PostgreSQL 16.x storing preference assessments, visual style profiles, catalog items, motif story knowledge, narrative profiles, historical references, and snapshot associations.
- **Migration Job (`migrate`)**: One-shot startup container running Alembic database schema migrations (`alembic upgrade head`).
- **FastAPI Backend (`api`)**: Python 3.11-slim API serving preference assessments, Style DNA analysis, Visual Style Match, Narrative Affinity, and Historical Connection engines. Runs as non-root user `appuser`.
- **Next.js Frontend (`web`)**: Node.js 20-alpine standalone SSR application. Runs as non-root user `node`.
- **MinIO / Object Storage (`minio`)** *(Optional)*: S3-compatible object storage service for durable image storage.

---

## 2. Required Environment Variables & Secret Handling

### Configuration Variables (`.env.production`)
- `APP_ENV`: Must be set to `production`.
- `DEBUG`: Must be set to `false`.
- `DATABASE_URL`: Asynchronous PostgreSQL connection string (e.g., `postgresql+asyncpg://user:password@host:5432/dbname`). Default dev passwords are **forbidden** in production mode.
- `CORS_ORIGINS`: JSON list of exact web origins (e.g., `["https://carpetstyle.example.com"]`). Wildcard `*` is **forbidden** in production mode.
- `TRUSTED_HOSTS`: JSON list of allowed HTTP Host headers (e.g., `["carpetstyle.example.com", "api.example.com"]`). Wildcard `*` is **forbidden** in production mode.
- `STORAGE_BACKEND`: `local` or `s3`.
- `IMAGE_STORAGE_ROOT`: `/app/data/uploads` (for `local` storage).
- `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`: Required when `STORAGE_BACKEND=s3`.
- `RATE_LIMIT_PER_MINUTE`: Max requests per minute per IP for sensitive endpoints (default: `120`).
- `NEXT_PUBLIC_API_URL`: Absolute API endpoint URL for Next.js frontend build.

> **CRITICAL SECURITY RULE**: Never commit real passwords, secret keys, or credentials to version control. Pass credentials via secure environment injection or vault management.

---

## 3. Health & Readiness Probes

### Liveness Probe (`GET /health` / `GET /health/live`)
- **Purpose**: Verifies that the API container process is alive and responsive.
- **HTTP Status**: Always returns `200 OK` when process is running.
- **Dependency**: Independent of database or storage state.

### Readiness Probe (`GET /health/ready`)
- **Purpose**: Verifies database connectivity (`SELECT 1`) and image storage accessibility before routing traffic to the API worker.
- **HTTP Status**:
  - `200 OK` (Healthy): Database and storage checks pass (`{"status": "ready", "database": "healthy", "storage": "healthy"}`).
  - `503 Service Unavailable` (Not Ready): Returned if DB connection fails or storage is inaccessible (`{"status": "not_ready", "database": "unhealthy", "storage": "unhealthy"}`).
- **Rate Limit Exemption**: Health probes are explicitly exempt from rate limiting.

---

## 4. Structured Logging & Request Correlation

- **JSON Format**: In `production` mode, logs are formatted as single-line JSON objects containing `timestamp`, `level`, `service`, `request_id`, `logger`, and `message`.
- **Request Correlation ID (`X-Request-ID`)**:
  - Incoming requests with a valid `X-Request-ID` header (1-64 alphanumeric, hyphen, underscore chars) retain their ID.
  - Requests without a valid ID are assigned a generated UUID (`req_...`).
  - Response headers include `X-Request-ID`.
- **Sensitive Data Redaction**: Loggers automatically redact sensitive keys (`password`, `secret`, `token`, `authorization`, `cookie`, `database_url`).
- **Error Privacy**: Unhandled 500 exceptions log tracebacks internally with `request_id`, but return a sanitized client error without leaking python stack traces.

---

## 5. Bounded Rate Limiting & Abuse Prevention

- **Policy**: Requests to non-health endpoints are rate limited per client IP (default: `120` req/min).
- **Exceeded Limit**: Returns HTTP `429 Too Many Requests` with a `Retry-After: 60` header and structured error body (`RATE_LIMIT_EXCEEDED`).
- **Limitation Notice**: The default rate limiter operates in-memory per container instance. Multi-instance distributed rate limiting requires external gateway policy enforcement.

---

## 6. Database Backup & Disaster Recovery

### PostgreSQL Backup (`scripts/backup_postgres.py`)
Run database backups before any deployment or schema migration:
```bash
python scripts/backup_postgres.py
```
This produces a timestamped compressed backup file: `data/backups/carpet_db_backup_YYYYMMDD_HHMMSS.sql.gz`.

### Restoration Procedure
To restore a backup into a target database:
```bash
gunzip -c data/backups/carpet_db_backup_YYYYMMDD_HHMMSS.sql.gz | psql -h localhost -U carpet_user -d carpet_db
```

### Storage Consistency
Database backup and image file storage backups must be performed synchronously so that `CarpetImageModel` database records match stored disk/S3 objects.

---

## 7. Failure Scenarios & Troubleshooting

### Failure Scenario 1: Database Unreachable
- **Symptom**: `/health/ready` returns HTTP 503 (`database: unhealthy`). API returns HTTP 500 for DB queries.
- **Action**: Check PostgreSQL container logs (`docker compose -f docker-compose.prod.yml logs postgres`). Verify connection string, port binding, and disk space.

### Failure Scenario 2: Storage Unwritable / Full
- **Symptom**: Image uploads fail with HTTP 500 (`ImageStorageFailedError`). `/health/ready` returns HTTP 503.
- **Action**: Check volume permissions (`/app/data/uploads` owned by `10001:10001`). Verify host volume mount and free disk space.

### Failure Scenario 3: Database Migration Failure
- **Symptom**: Migration container (`carpet_migrate_prod`) exits with non-zero status. API container fails to start (`service_completed_successfully` unsatisfied).
- **Action**: Inspect migration logs (`docker logs carpet_migrate_prod`). Restore database from pre-migration backup before attempting code rollback.

---

## 8. Rollback Strategy

1. **Application Image Rollback**: Revert container image tags to the previous known good release.
2. **Database Rollback Policy**: **DO NOT** execute automatic `alembic downgrade` commands in production. Database migrations must be manually reviewed and tested prior to rollback.

---

## 9. Public Authentication Limitation Warning

> **IMPORTANT OPERATIONAL NOTICE**: The Carpet Style & Story Match v1 application does **NOT** provide native user authentication or role-based access control (RBAC). Public internet deployments **MUST** restrict access via network firewalls, VPNs, reverse proxy authentication (e.g., OAuth2 Proxy, Authelia), or API Gateways.
