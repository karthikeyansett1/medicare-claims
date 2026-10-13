PYTHON ?= $(if $(wildcard .venv/bin/python),$(CURDIR)/.venv/bin/python,python3)
MEDICARE_SAMPLES ?= 1,2
export MEDICARE_SAMPLES
SAMPLES = $(subst $(comma), ,$(MEDICARE_SAMPLES))
comma := ,
UV_CACHE_DIR ?= /tmp/medicare-uv-cache
export UV_CACHE_DIR
export UV_PYTHON_INSTALL_DIR := $(CURDIR)/.python
.PHONY: help setup lock db-up verify download verify-data test profile bronze verify-bronze test-db
help:
	@echo "setup: install Python 3.11 and locked dependencies"
	@echo "db-up: start local PostgreSQL 16 (requires .env)"
	@echo "verify: check dependencies, connection, and startup schemas"
setup:
	@if command -v uv >/dev/null 2>&1; then uv venv --python 3.11 .venv && uv pip sync --python .venv/bin/python requirements.txt; else python3 -c "import sys; assert sys.version_info[:2] == (3, 11), 'Python 3.11 required'" && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt; fi
	$(MAKE) dbt-deps PYTHON=$(CURDIR)/.venv/bin/python
lock:
	uv pip compile --python $(PYTHON) requirements.in -o requirements.txt
db-up:
	docker compose --env-file .env up -d --wait db
verify:
	$(PYTHON) -c "import psycopg, dbt, sqlglot; print('PASS: dependency imports')"
	$(PYTHON) -m ingest.db

download:
	@for sample in $(SAMPLES); do $(PYTHON) -m ingest.download --sample $$sample || exit $$?; done
verify-data:
	@for sample in $(SAMPLES); do $(PYTHON) -m ingest.download --verify-only --sample $$sample || exit $$?; done
	@for sample in $(SAMPLES); do $(PYTHON) -m ingest.verify_sources --sample $$sample || exit $$?; done
test:
	$(PYTHON) -m pytest tests/ -q

profile:
	@for sample in $(SAMPLES); do $(PYTHON) -m ingest.profile_raw --sample $$sample || exit $$?; done

bronze: download
	$(PYTHON) -m ingest.load_bronze
verify-bronze:
	$(PYTHON) -m ingest.load_bronze --verify-only
test-db:
	RUN_DB_TESTS=1 $(PYTHON) -m pytest tests/ -q

.PHONY: silver verify-silver dbt-debug
dbt-debug:
	$(PYTHON) -m ingest.run_dbt debug
silver:
	$(PYTHON) -m ingest.run_dbt build --select staging silver tag:step4
verify-silver:
	$(PYTHON) -m ingest.verify_silver

.PHONY: gold verify-gold benchmark-gold dbt-docs
gold:
	$(PYTHON) -m ingest.run_dbt build --select em_office_visit_codes
	$(PYTHON) -m ingest.run_dbt build --select gold
verify-gold:
	$(PYTHON) -m ingest.verify_gold
benchmark-gold:
	$(PYTHON) -m ingest.benchmark_gold
dbt-docs:
	$(PYTHON) -m ingest.run_dbt docs generate

.PHONY: dbt-deps quality-build sql-lint
dbt-deps:
	$(PYTHON) -m ingest.run_dbt deps
quality-build: dbt-deps
	$(PYTHON) -m ingest.run_dbt build
sql-lint:
	$(PYTHON) -m ingest.run_sqlfluff lint dbt_project/models

.PHONY: attribution verify-attribution
attribution:
	$(PYTHON) -m ingest.run_dbt build --select tag:step7
verify-attribution:
	$(PYTHON) -m ingest.verify_attribution

.PHONY: grouper verify-grouper
grouper:
	$(PYTHON) -m ingest.clean_ccs
	$(PYTHON) -m ingest.run_dbt build --select ccs_dx_map+

verify-grouper:
	$(PYTHON) -m ingest.verify_ccs

.PHONY: readmissions verify-readmissions
readmissions:
	$(PYTHON) -m ingest.run_dbt --no-partial-parse build --select tag:step9
verify-readmissions:
	$(PYTHON) -m ingest.verify_readmissions

.PHONY: metrics verify-metrics core-build pipeline-build
metrics:
	$(PYTHON) -m analysis.risk_model
	$(PYTHON) -m ingest.run_dbt --no-partial-parse build --select tag:step10 source:analysis.expected_cost
verify-metrics:
	$(PYTHON) -m ingest.verify_metrics
# Fresh warehouse order: upstream dbt, Python expected costs, dependent mart.
core-build:
	$(PYTHON) -m ingest.run_dbt --no-partial-parse build --exclude tag:step10 source:analysis.expected_cost
pipeline-build: core-build
	$(MAKE) metrics

.PHONY: compare verify-comparison
compare:
	$(PYTHON) -m analysis.compare_methods
	$(PYTHON) -m analysis.render_findings
verify-comparison:
	$(PYTHON) -m analysis.verify_comparison

.PHONY: assistant-role assistant assistant-smoke
assistant-role:
	$(PYTHON) -m assistant.setup_role
assistant:
	.venv/bin/streamlit run assistant/app.py --server.address 127.0.0.1
assistant-smoke:
	$(PYTHON) -m assistant.smoke

.PHONY: export dashboard
export:
	$(PYTHON) -m analysis.export_dashboard
dashboard:
	.venv/bin/streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8502

# Sequential recipes are deliberate: make -j must not race database stages.
.PHONY: ci all roles build analyze _fixture-pipeline schemas
ci:
	$(PYTHON) -m ingest.runtime
schemas:
	$(PYTHON) -c "from ingest.db import get_conn, ROOT; c=get_conn(); c.execute((ROOT/'sql/init/01_schemas.sql').read_text()); c.commit(); c.close()"
roles: assistant-role
build: pipeline-build
analyze: compare
all:
	$(MAKE) setup
	$(MAKE) db-up
	$(MAKE) schemas
	$(MAKE) download
	$(MAKE) profile
	$(MAKE) bronze
	$(MAKE) dbt-deps
	$(MAKE) pipeline-build
	$(MAKE) compare
	$(MAKE) export
_fixture-pipeline:
	$(PYTHON) -m ingest.runtime --guard
	$(MAKE) schemas
	$(MAKE) profile
	$(PYTHON) -m ingest.load_bronze
	$(MAKE) dbt-deps
	$(MAKE) pipeline-build
	$(MAKE) compare
	$(MAKE) export
	$(MAKE) verify-bronze verify-silver verify-gold verify-attribution verify-grouper verify-readmissions verify-metrics verify-comparison
	$(MAKE) assistant-role
	$(MAKE) sql-lint
	$(MAKE) test
