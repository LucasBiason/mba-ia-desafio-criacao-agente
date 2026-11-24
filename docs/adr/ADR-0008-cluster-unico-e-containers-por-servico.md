---
status: accepted
date: 2026-11-23
decision-makers: [Responsável pelo produto]
source: ../design/architecture.md
source_section: "9. Observabilidade e operação"
feature: F01
spec: ../specs/F01-fundacao/spec.md
spec_section: "3. Decisões técnicas"
---

# ADR-0008: Compor o cluster com containers pertencentes aos serviços

## Contexto e problema

A operação local precisa representar todos os componentes do residencial em uma composição compreensível. A raiz é o agregador do projeto; as unidades executáveis são os serviços. Sua configuração deve permitir reproduzir o portal e o contrato do assistente sem sobrepor manifestos de execução.

Origem: [F01](../prd/functional/F01-fundacao.md), [spec F01](../specs/F01-fundacao/spec.md) e [arquitetura](../design/architecture.md). A organização foi definida explicitamente pelo responsável pelo produto. Este registro complementa os ADRs 0004 e 0007; mantém a delimitação de persistência do ADR-0006.

## Fatores da decisão

Propriedade dos artefatos de execução, composição única, configuração privada separada do código, preservação dos dados e repetibilidade do build.

## Opções consideradas

- Um manifesto em configs e Dockerfile/entrypoint em cada serviço: opção escolhida.
- Imagem de aplicação na raiz e múltiplos manifestos sobrepostos: organização rejeitada para este produto.

## Resultado da decisão

O cluster é definido por `configs/compose.yaml`, com todos os serviços do produto. O portal usa a porta fixa 8770 e a API do assistente a porta fixa 8000. `configs/.env` contém a configuração privada e permanece ignorado; `configs/.env.example` é o exemplo distribuído. Não há outros arquivos nessa pasta.

Cada serviço possui seu Dockerfile e entrypoint. O frontend pertence a `services/frontend`; infraestrutura de suporte e operações ficam em `infra`. O manifesto `pyproject.toml` e o lock `uv.lock` ficam na raiz para permitir `uv sync` literal e fixar a resolução de todos os serviços. São metadados de distribuição; a raiz não hospeda um servidor nem um Dockerfile de aplicação. `infra/python/pyproject.toml` contém somente as regras Ruff e o código dos toolkits fica em `infra/packages`.

O portal autenticado e a API do assistente compartilham a operação do cluster, mas conservam redes, rotas e persistência próprias. A API do assistente não é um caminho alternativo para acessar os dados do portal. Gemini real é o provedor do ambiente de uso; modelos injetados pertencem exclusivamente aos testes unitários.

### Consequências

- Positiva: um comando de partida representa o conjunto de componentes e cada serviço possui seus artefatos de container.
- Negativa: mudanças comuns de build precisam ser mantidas coerentes entre os Dockerfiles dos serviços.
- Neutra: a organização dos arquivos não modifica identidades, fixtures, nomes dos volumes existentes nem concede aceite funcional.

### Confirmação

Construir as imagens, validar o manifesto sem imprimir credenciais, iniciar uma composição isolada e verificar o portal, as seis rotas do assistente e as fronteiras privadas. Repetir a preparação e reiniciar os serviços deve preservar os dados. Resultados de execução e aceite humano permanecem fora do repositório.
