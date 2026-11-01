# DocuMind

Enterprise Document Intelligence & Grounded RAG Platform.

DocuMind is being built to turn organizational documents into searchable,
traceable evidence. The target system combines format-specific parsing and OCR,
structured extraction, hybrid retrieval, and answers that cite source passages or
explicitly abstain when evidence is insufficient.

**Current stage: Milestone 1, foundation.** The API, relational schema, migrations,
worker bootstrap, operational telemetry and deployment configuration are implemented.
Document ingestion, authentication endpoints, retrieval, RAG, evaluation and the
React dashboard are subsequent milestones, not working features of this revision.
See [actual validation and pending work](docs/progress.md).

## Architecture and stack

A FastAPI modular monolith uses PostgreSQL as the source of truth, Redis for work
delivery, Qdrant for the future dense/sparse search index, and independently scaled
Celery workers. SQLAlchemy 2 and Pydantic 2 define persistence and configuration.
Prometheus and Grafana provide operational visibility. Python dependencies are
pinned in lockfiles; containers use explicit version tags.

See the [architecture and request-flow diagrams](docs/architecture.md) and
[eight-milestone implementation plan](docs/implementation_plan.md).

## Requirements

- Python 3.12+ for development; Docker containers use Python 3.12.
- Docker Engine/Desktop with Compose v2 for the full foundation stack.
- Internet access to install packages and pull images.
- Model memory/GPU requirements will be documented when ML integration is delivered;
  the foundation does not download models or require API keys.

## Local setup

From the repository root, on PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.lock
python scripts/init_env.py
docker compose up --build -d --wait --wait-timeout 180
python scripts/smoke.py
```

The setup script creates `.env` with random local secrets and refuses to overwrite
an existing file. Keep this file private. On POSIX, activate `.venv/bin/activate`
and use `python` for the same commands. No real credentials are included in source.

- API documentation: <http://localhost:8000/api/docs>
- Liveness: <http://localhost:8000/api/v1/health/live>
- Readiness: <http://localhost:8000/api/v1/health/ready>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000> (user `admin`, password from your `.env`)

The worker is bootstrapped but no document tasks exist yet. The frontend service
will be added with Milestone 6. Grafana's charts show collected data or empty states.

## Development without Docker

Unit tests use SQLite with foreign keys enabled. This is a testing convenience;
PostgreSQL remains required for normal application use. The app does not create or
migrate tables on startup.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m mypy app
Set-Location ..
.\.venv\Scripts\python.exe -m ruff check backend scripts
.\.venv\Scripts\python.exe -m ruff format --check backend scripts
```

To run the API on the host with Compose dependencies, see
[deployment and migrations](docs/deployment.md). Configuration fields and their
defaults are documented in [configuration](docs/configuration.md).

## Testing and CI

Tests cover settings validation, operational endpoints, dependency failure/timeouts,
secret redaction, bounded metric labels, tenant foreign-key constraints,
deduplication, deletion cascades, and migration upgrade/downgrade/model parity.
An opt-in integration test checks real PostgreSQL, Redis and Qdrant. CI defines a
Python 3.12/3.13 matrix, Ruff, mypy, pytest, dependency audit, Docker builds and a
Compose smoke test. A checked-in workflow is not evidence that hosted CI passed.

## Security and limitations

Composite tenant constraints are a storage integrity layer, not a substitute for
authorization. No user-facing document routes are exposed yet. Read the
[security model](docs/security.md) before deployment. API errors are sanitized;
request logs omit bodies, query strings and credentials. Operational endpoints
must be restricted by ingress before any public deployment.

Docker startup, production deployment and model performance are not claimed until
they are actually tested. Image tags are versioned but not digest-pinned; dependency
locks pin versions but do not yet include artifact hashes. Base image security and
future model licenses require review before public deployment.

## Evaluation and screenshots

No retrieval benchmarks have run because retrieval is not implemented in this
milestone. No correctness/faithfulness figures or UI screenshots are fabricated.
The planned evaluation protocol is in [evaluation](docs/evaluation.md). Screenshots
will be captured from the working frontend in Milestone 6.

Next: authenticated document upload, local object storage, parsers/OCR and reliable
background ingestion. The full roadmap is tracked in the implementation plan.
