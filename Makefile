.DEFAULT_GOAL := help
ENV ?= local
PYTHON ?= python3
AURORA_PORT ?= 8767
AURORA_TEST_PORT ?= 8768
AURORA_URL ?= http://127.0.0.1:$(AURORA_TEST_PORT)
export AURORA_PORT
COMPOSE := docker compose
ifeq ($(ENV),dev)
COMPOSE := docker compose -f compose.yaml -f configs/compose.dev.yaml
else ifneq ($(ENV),local)
$(error ENV deve ser local ou dev)
endif

.PHONY: help setup config build up stop down ps logs test test-unit test-ui test-runtime initialize seed-agenda unseed-agenda
help: ## Mostrar os comandos disponíveis (ENV=local|dev)
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
setup: ## Preparar credenciais locais sem sobrescrever .env
	@$(PYTHON) configs/setup_local.py
config: setup ## Validar Compose sem imprimir credenciais
	@$(COMPOSE) config -q
build: setup ## Construir as imagens
	@$(COMPOSE) build
up: setup ## Construir e iniciar aguardando prontidão
	@$(COMPOSE) up --build --wait
initialize: setup ## Preparar schema e dados iniciais explicitamente
	@$(COMPOSE) up --wait identity-db condo-db
	@$(COMPOSE) build identity-init condo-init
	@$(COMPOSE) run --rm --no-deps identity-init
	@$(COMPOSE) run --rm --no-deps condo-init
stop: ## Parar mantendo contêineres e dados
	@$(COMPOSE) stop
down: ## Remover contêineres e redes preservando volumes
	@$(COMPOSE) down
ps: ## Consultar os serviços
	@$(COMPOSE) ps
logs: ## Acompanhar logs (SERVICE opcional)
	@$(COMPOSE) logs --follow $(SERVICE)
test: ## Testar a API e o OpenAPI da instância local
	@AURORA_URL="$(AURORA_URL)" uv run --with pytest pytest services/apartments/tests/integration/test_api.py services/apartments/tests/integration/test_openapi.py -q
test-unit: ## Testar validação de identidade da aplicação
	@uv run --with pytest==8.4.2 python -m pytest services/authentication/tests -q
test-ui: ## Testar foco móvel (requer Playwright e credencial sintética no ambiente)
	@AURORA_URL="$(AURORA_URL)" $(PYTHON) web/tests/test_mobile_navigation.py
test-runtime: ## Provar reinício na instância descartável indicada
	@AURORA_URL="$(AURORA_URL)" uv run services/apartments/tests/integration/test_runtime.py
seed-agenda: ## Inserir reservas sintéticas na instância local
	@$(PYTHON) tools/seed_agenda.py add
unseed-agenda: ## Remover apenas as reservas sintéticas geradas
	@$(PYTHON) tools/seed_agenda.py remove

# Pinned tool, independent from the operational application environment.
RUFF := uvx --from ruff==0.14.2 ruff
.PHONY: lint format-check
lint: ## Verificar erros Python com Ruff fixado (não modifica arquivos)
	@$(RUFF) check .
format-check: ## Conferir formatação Python sem modificar arquivos
	@$(RUFF) format --check .
.PHONY: test-agent-offline
test-agent-offline: ## Testar agente com modelos injetados, sem Gemini (requer uv sync --frozen)
	@PYTHONDONTWRITEBYTECODE=1 uv run --frozen python -m unittest discover -s services/agent/tests -p 'test_*.py' -v
.PHONY: lint-imports
lint-imports: ## Validar imports no escopo QA sem alterar bootstrap/registro ORM
	@$(RUFF) check --select I tools/academic_concurrency_benchmark.py tools/academic_release_qa.py tools/portal_playwright_confirmations.py services/agent/tests/test_provider_transport.py

# Baseline estático do agente; não equivale a mypy --strict.
MYPY := uvx --from mypy==1.19.1 mypy
TYPECHECK_PYTHON ?= $(CURDIR)/.venv/bin/python
.PHONY: typecheck-agent
typecheck-agent: ## Validar tipos do agente com fontes internas e dependências locais
	@MYPYPATH="$(CURDIR)/packages/microservice-toolkit/src:$(CURDIR)/packages/aurora-toolkit/src:$(CURDIR)/services/agent/tests" $(MYPY) --no-incremental --explicit-package-bases --python-executable "$(TYPECHECK_PYTHON)" services/agent
