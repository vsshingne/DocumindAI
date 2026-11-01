.PHONY: install lint test typecheck up down migrate smoke
install:
	python -m pip install -r backend/requirements-dev.lock
lint:
	python -m ruff check backend scripts
	python -m ruff format --check backend scripts
test:
	cd backend && python -m pytest -q
typecheck:
	cd backend && python -m mypy app
up:
	docker compose up --build -d --wait
down:
	docker compose down
migrate:
	docker compose run --rm migrate
smoke:
	python scripts/smoke.py
