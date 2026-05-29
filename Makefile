.PHONY: up-dev up-team down-dev down-team dev-up dev-down team-up team-down logs-dev logs-team up dev-seed dev-bootstrap test eval build-prod

# DEV ENVIRONMENT — full bootstrap (build + start + seed dev/CI demo data).
dev-up: dev-bootstrap

# Internal target — orchestrates the full first-run bootstrap.
dev-bootstrap:
	@echo "▶ Building images & starting containers..."
	docker compose -f docker-compose.dev.yml --env-file .env.dev up -d --build
	@echo "▶ Waiting for Postgres to accept connections..."
	@for i in $$(seq 1 30); do \
	  docker exec nexus-vector-db pg_isready -U admin -d nexus_knowledge >/dev/null 2>&1 && break; \
	  sleep 1; \
	done
	@echo "▶ Waiting for API container to come up..."
	@for i in $$(seq 1 60); do \
	  docker exec nexus-api curl -fs http://localhost:8000/health >/dev/null 2>&1 && break; \
	  sleep 1; \
	done
	@$(MAKE) --no-print-directory dev-seed
	@echo ""
	@echo "✅ Backend stack ready."
	@echo "   API docs  → http://localhost:8002/docs"
	@echo "   pgAdmin   → http://localhost:5051"
	@echo "   Redis     → http://localhost:6380"

dev-down:
	docker compose -f docker-compose.dev.yml --env-file .env.dev down -v

# TEAM ENVIRONMENT (full destroy)
team-up:
	docker compose -p team -f docker-compose.yml --env-file .env.team up -d

team-down:
	docker compose -p team -f docker-compose.yml --env-file .env.team down -v


# ------------------------------
# NON-DESTRUCTIVE COMMANDS (NO REBUILD)
# ------------------------------

# Start ONLY DEV (no rebuild)
up-dev:
	docker compose -f docker-compose.dev.yml up -d
	@echo "🚀 DEV started without rebuild."

# Start ONLY TEAM (no rebuild)
up-team:
	docker compose -p team -f docker-compose.yml up -d
	@echo "🚀 TEAM started without rebuild."

# Start BOTH (no rebuild)
up: up-dev up-team
	@echo "🚀 DEV & TEAM started without rebuild."


# ------------------------------
# NON-DESTRUCTIVE DOWN COMMANDS
# ------------------------------
down-dev:
	docker compose -f docker-compose.dev.yml down
	@echo "🛑 DEV stopped (volumes preserved)."

down-team:
	docker compose -p team -f docker-compose.yml down
	@echo "🛑 TEAM stopped (volumes preserved)."


# Apply the dev/CI test-data seed to an existing dev container. The schema
# and clean production seed are already in place from init_db.sql (auto-applied
# by the Postgres container entrypoint on first boot). This layers all dev/CI
# demo data (Section 1) plus the RBAC role-grant block.
# Uses stdin piping (docker exec -i) because bind-mounted files are unreliable on macOS VirtioFS.
dev-seed:
	@echo "Applying dev/CI test-data seed..."
	docker exec -i nexus-vector-db psql -U admin -d nexus_knowledge < backend/scripts/seed_test_data.sql
	@echo "  ✓ test-data seed applied"

# LOGS
logs-dev:
	docker compose -f docker-compose.dev.yml logs -f

logs-team:
	docker compose -f docker-compose.yml logs -f


# ============================================================
# PHASE 3 — CI/CD & MLOps
# ============================================================

# Run pytest suite with coverage gate (fail if under 80%)
test:
	@echo "▶ Running pytest with coverage (threshold: 80%)..."
	cd backend && python -m pytest tests/ -v --tb=short \
	  --cov=app \
	  --cov-config=.coveragerc \
	  --cov-report=term-missing \
	  --cov-fail-under=80

# Run golden dataset evaluation against a running dev stack
eval:
	@echo "▶ Running golden dataset evaluation..."
	python backend/scripts/run_evaluation.py

# Build the multi-stage production image
build-prod:
	@echo "▶ Building production image (multi-stage)..."
	docker build -f backend/Dockerfile.prod -t nexus-api:latest backend/