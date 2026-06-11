.PHONY: up down dev migrate test test-db test-db-down build-skills

up:            ## Run the full stack (postgres + server + nightly backup)
	docker compose up --build

down:
	docker compose down

dev:           ## Run the server locally against compose postgres
	uv run uvicorn server.app:app --reload

migrate:       ## Apply migrations to DATABASE_URL (or compose default)
	uv run alembic upgrade head

test-db:       ## Throwaway postgres for the test suite (port 5433)
	docker run -d --name postcard-test-db -p 127.0.0.1:5433:5432 \
		-e POSTGRES_USER=postcard -e POSTGRES_PASSWORD=postcard -e POSTGRES_DB=postcard_test \
		postgres:16 || true
	@until docker exec postcard-test-db pg_isready -U postcard -d postcard_test >/dev/null 2>&1; do sleep 0.5; done

test-db-down:
	docker rm -f postcard-test-db || true

test: test-db  ## Run the full suite against the throwaway postgres
	TEST_DATABASE_URL=postgresql+psycopg://postcard:postcard@localhost:5433/postcard_test uv run pytest -q

build-skills:  ## Regenerate plugin skills from server/guidance
	uv run python scripts/build_plugin_skills.py
