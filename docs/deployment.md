# Deployment and migrations

## Full local stack

1. Run `python scripts/init_env.py` from the repository root.
2. Run `docker compose config --quiet` to validate configuration without printing secrets.
3. Run `docker compose up --build -d --wait --wait-timeout 180`.
4. Run `python scripts/smoke.py`.

PostgreSQL and Redis have native health probes. A bounded one-shot application
container checks Qdrant because its image does not promise curl/wget. The migration
container must succeed before the API starts; the worker waits for API health.
Readiness separately checks all dependencies and the exact schema revision.

Use `docker compose ps -a` and `docker compose logs backend worker migrate` for
diagnostics. Do not paste secrets or complete environment output into issue reports.
Stop with `docker compose down`; named volumes preserve documents and service data.
Deleting volumes destroys local data and is not part of the normal stop command.

## Host development

Start only the data services with:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis qdrant
```

The override binds PostgreSQL, Redis and Qdrant to loopback. From the root, with
the virtual environment activated:

```sh
python -m alembic -c backend/alembic.ini upgrade head
python -m uvicorn app.main:create_app --factory --app-dir backend --no-access-log
```

For the optional integration test, use an isolated database and export the
DATABASE_URL, REDIS_URL and QDRANT_URL variables, set `DOCUMIND_INTEGRATION=1`,
then run `python -m pytest -m integration -v` from `backend`. The test applies
migrations but does not erase an existing database. Never point test jobs at
production. The CI Compose stack is isolated and disposable.

## Migrations

The initial revision explicitly creates all tables and constraints. It never calls
`metadata.create_all()` during migration or application startup. From the root:

```sh
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini check
```

To add a revision, run `revision --autogenerate -m description`, review generated
SQL and migration code, and test upgrade/downgrade on an isolated database. A
downgrade may drop data: back up and review it before any operational use.
Update the readiness schema revision when introducing a new migration.

## Production considerations

This Compose configuration is a local, production-oriented starting point, not a
production certification. Use `APP_ENV=production`, a strong JWT secret and explicit
HTTPS CORS origins. Add TLS ingress, restrict `/metrics` and health diagnostics to
operators, use managed secrets, back up PostgreSQL/Qdrant/storage, monitor disk
capacity, and define restore/retention procedures. Keep PostgreSQL, Redis and Qdrant
off public interfaces. Current Redis/Qdrant connections assume an isolated trusted
Compose network; a shared network requires service authentication/TLS configuration.

The API runs as UID 10001 without Linux capabilities. One API process per container
keeps Prometheus metrics accurate; scale using replicas and scrape each replica.
Before release, audit container images and lock them by digest. Worker crash recovery
will only be claimed after ingestion tasks and restart tests exist in Milestone 2.
