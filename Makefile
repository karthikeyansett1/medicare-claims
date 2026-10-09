UV_CACHE_DIR ?= /tmp/medicare-uv-cache
export UV_CACHE_DIR
export UV_PYTHON_INSTALL_DIR := $(CURDIR)/.python
.PHONY: help setup lock db-up verify download verify-data test profile bronze verify-bronze test-db
help:
	@echo "setup: install Python 3.11 and locked dependencies"
	@echo "db-up: start local PostgreSQL 16 (requires .env)"
	@echo "verify: check dependencies, connection, and startup schemas"
setup:
	uv venv --python 3.11 .venv
	uv pip sync --python .venv/bin/python requirements.txt
lock:
	uv pip compile --python .venv/bin/python requirements.in -o requirements.txt
db-up:
	docker compose --env-file .env up -d --wait db
verify:
	.venv/bin/python -c "import psycopg, dbt, sqlglot; print('PASS: dependency imports')"
	.venv/bin/python -m ingest.db

download:
	.venv/bin/python -m ingest.download
verify-data:
	.venv/bin/python -m ingest.download --verify-only
	.venv/bin/python -m ingest.verify_sources
test:
	.venv/bin/python -m pytest tests/ -q

profile:
	.venv/bin/python -m ingest.profile_raw

bronze: download
	.venv/bin/python -m ingest.load_bronze
verify-bronze:
	.venv/bin/python -m ingest.load_bronze --verify-only
test-db:
	RUN_DB_TESTS=1 .venv/bin/python -m pytest tests/ -q

.PHONY: silver verify-silver dbt-debug
dbt-debug:
	.venv/bin/python -m ingest.run_dbt debug
silver:
	.venv/bin/python -m ingest.run_dbt build --select staging silver tag:step4
verify-silver:
	.venv/bin/python -m ingest.verify_silver
