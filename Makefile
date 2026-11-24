.DEFAULT_GOAL := help
PYTHON ?= python3
AURORA_URL ?=
AURORA_ENV_FILE ?= $(CURDIR)/configs/.env
UV_PROJECT_ENVIRONMENT ?= $(HOME)/.cache/aurora/python
export UV_PROJECT_ENVIRONMENT
export PYTHONDONTWRITEBYTECODE := 1
COMPOSE := docker compose --env-file $(AURORA_ENV_FILE) --file configs/compose.yaml
UV := uv run --frozen
RUFF := uvx --from ruff==0.14.2 ruff
.PHONY: help setup config build up initialize restore stop down ps logs sync test test-unit test-agent-offline test-ui test-runtime lint format-check lint-imports typecheck-agent seed-agenda unseed-agenda
help: ## Mostrar os comandos disponíveis
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
setup: ## Preparar configs/.env preservando os valores existentes
	@$(PYTHON) infra/setup_local.py
config: setup ## Validar a configuração sem imprimir credenciais
	@$(COMPOSE) config --quiet
build: setup ## Construir as imagens de todos os serviços
	@$(COMPOSE) build
up: setup ## Construir e levantar o cluster completo
	@$(COMPOSE) up --build --wait
initialize: setup ## Preparar os bancos sem sobrescrever dados existentes
	@$(COMPOSE) up --build --wait identity-init condo-init agent-init
restore: setup ## Restaurar dados do assistente e invalidar suas sessões
	@$(COMPOSE) stop agent-a agent-b
	@$(COMPOSE) run --rm --no-deps agent-init api restore --confirm-restore
	@$(COMPOSE) up --wait --no-deps agent-a agent-b agent-gateway
stop: ## Parar o cluster preservando seus dados
	@$(COMPOSE) stop
down: ## Remover contêineres e rede preservando os volumes
	@$(COMPOSE) down
ps: ## Consultar os serviços
	@$(COMPOSE) ps
logs: ## Acompanhar logs (SERVICE opcional)
	@$(COMPOSE) logs --follow $(SERVICE)
sync: ## Preparar Python em ambiente externo ao repositório
	@uv sync --frozen

test: ## Testar API e OpenAPI usando credenciais sintéticas no ambiente
	@test -n "$(AURORA_URL)" || (echo "Informe AURORA_URL explicitamente para a instância escolhida de teste." >&2; exit 2)
	@AURORA_URL="$(AURORA_URL)" $(UV) --with pytest python -m pytest services/apartments/tests/integration/test_api.py services/apartments/tests/integration/test_openapi.py -q -p no:cacheprovider
test-unit: ## Testar identidade e preparação de infraestrutura
	@$(UV) --with pytest python -m pytest services/authentication/tests infra/tests -q -p no:cacheprovider
test-agent-offline: ## Testar o agente com modelos injetados e sem chamadas Gemini
	@$(UV) python -m unittest discover -s services/agent/tests -p 'test_*.py'
test-ui: ## Validar navegação em uma instância sintética explícita
	@test -n "$(AURORA_URL)" || (echo "Informe AURORA_URL explicitamente para a instância escolhida de teste." >&2; exit 2)
	@AURORA_URL="$(AURORA_URL)" $(PYTHON) services/frontend/tests/test_mobile_navigation.py
test-runtime: ## Validar reinício em composição de teste separada
	@test -n "$(AURORA_URL)" || (echo "Informe AURORA_URL explicitamente para a instância escolhida de teste." >&2; exit 2)
	@AURORA_URL="$(AURORA_URL)" AURORA_ENV_FILE="$(AURORA_ENV_FILE)" $(UV) services/apartments/tests/integration/test_runtime.py
lint: ## Verificar erros Python sem modificar arquivos
	@$(RUFF) check --config infra/python/pyproject.toml --no-cache .
format-check: ## Conferir formatação sem modificar arquivos
	@$(RUFF) format --config infra/python/pyproject.toml --no-cache --check .
lint-imports: ## Validar imports Python sem modificar arquivos
	@$(RUFF) check --config infra/python/pyproject.toml --no-cache --select I services/agent/tests services/agent/runtime
typecheck-agent: ## Validar os tipos do agente com cache externo
	@MYPYPATH="$(CURDIR)/infra/packages/microservice-toolkit/src:$(CURDIR)/infra/packages/aurora-toolkit/src:$(CURDIR)/services/agent/tests" uvx --from mypy==1.19.1 mypy --cache-dir /tmp/aurora-mypy-cache --explicit-package-bases --python-executable "$(UV_PROJECT_ENVIRONMENT)/bin/python" services/agent
seed-agenda: ## Criar reservas sintéticas de demonstração na instância local
	@$(PYTHON) infra/operations/seed_agenda.py add
unseed-agenda: ## Retirar somente as reservas sintéticas de demonstração
	@$(PYTHON) infra/operations/seed_agenda.py remove

.PHONY: test-assistant
test-assistant: ## Conferir conversa contínua e histórico no portal local
	@AURORA_UI_URL=http://127.0.0.1:8770 $(PYTHON) services/frontend/tests/test_assistant_conversation.py
