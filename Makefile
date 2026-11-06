.DEFAULT_GOAL := dev
CHECK_COMPOSE = docker compose -p stockscope-check -f compose.yaml -f compose.fixture.yaml
RUN = $(CHECK_COMPOSE) run --rm --no-deps -T
BACKEND = $(RUN) -e DATABASE_URL=sqlite:////tmp/stockscope-check.db backend
FRONTEND = $(RUN) frontend

.PHONY: dev stop status logs test lint format format-check typecheck check build smoke rebuild

dev:
	docker compose up -d
stop:
	docker compose down
status:
	docker compose ps
logs:
	docker compose logs -f
rebuild:
	docker compose up --build -d

test:
	$(BACKEND) pytest -q
	$(FRONTEND) npm run test
lint:
	$(BACKEND) ruff check --config pyproject.toml . /workspace/scripts
	$(FRONTEND) npm run lint
format:
	$(RUN) -v ./backend/tests:/workspace/backend/tests -v ./scripts:/workspace/scripts backend ruff format --config pyproject.toml app tests /workspace/scripts
	$(RUN) -v ./frontend:/app -v /app/node_modules frontend npm run format
format-check:
	$(BACKEND) ruff format --config pyproject.toml --check --silent app tests /workspace/scripts
	$(FRONTEND) npm run format:check
typecheck:
	$(FRONTEND) npm run typecheck
check: lint format-check typecheck test build
	$(FRONTEND) npm run ci
build:
	$(FRONTEND) npm run build
# This native harness refuses occupied ports and uses temporary fixture storage.
# Stop Compose first; local Playwright/browser dependencies must already exist.
smoke:
	backend/.venv/bin/python backend/tests/browser_smoke.py
