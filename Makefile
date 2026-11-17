.DEFAULT_GOAL := help
ENV ?= local
PYTHON ?= python3
AURORA_PORT ?= 8767
AURORA_URL ?= http://127.0.0.1:$(AURORA_PORT)
export AURORA_PORT
COMPOSE := docker compose
ifeq ($(ENV),dev)
COMPOSE := docker compose -f compose.yaml -f configs/compose.dev.yaml
else ifneq ($(ENV),local)
$(error ENV deve ser local ou dev)
endif

.PHONY: help setup config build up stop down ps logs test test-runtime seed-agenda unseed-agenda
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
test-runtime: ## Provar reinício na instância descartável indicada
	@AURORA_URL="$(AURORA_URL)" uv run services/apartments/tests/integration/test_runtime.py
seed-agenda: ## Inserir reservas sintéticas na instância local
	@$(PYTHON) dados/seed_agenda.py add
unseed-agenda: ## Remover apenas as reservas sintéticas geradas
	@$(PYTHON) dados/seed_agenda.py remove
