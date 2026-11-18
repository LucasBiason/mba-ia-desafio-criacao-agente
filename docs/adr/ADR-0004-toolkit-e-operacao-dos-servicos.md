---
status: accepted
date: 2026-11-18
decision-makers: [Responsável pelo produto]
source: ../design/architecture.md
source_section: "10. Decisões, riscos e validação"
feature: F01
spec: ../specs/F01-fundacao/spec.md
spec_section: "3. Decisões técnicas"
---

# ADR-0004: Compartilhar infraestrutura HTTP e padronizar a operação

## Contexto e problema

Saúde, erros, autenticação de transporte e logs se repetem nos serviços. O padrão do produto exige toolkit compartilhado, health e Swagger por aplicação, Makefile, entrypoint e configuração de containers com modos claros.

Origem: [arquitetura](../design/architecture.md#10-decisões-riscos-e-validação), [PRD](../prd/index.md) e [spec F01](../specs/F01-fundacao/spec.md#3-decisões-técnicas). A formalização preserva as escolhas do produto e distingue a topologia observada das decisões aprovadas.

## Fatores da decisão

Responsabilidades explícitas, segurança por recurso, preservação dos dados e operação local reproduzível. A decisão é estrutural, precisa de justificativa rastreável e tem duração superior ao detalhe de uma implementação.

## Opções consideradas

- Toolkit compartilhado, Makefile e entrypoint explícito, opção escolhida.
- Infraestrutura duplicada e scripts soltos na raiz, forma rejeitada na organização do produto.

## Resultado da decisão

Vamos concentrar factory HTTP, middleware, logs sanitizados, correlação, erros e health no microservice-toolkit. Os serviços fornecem prontidão e contratos Swagger. Makefile é a interface operacional; Dockerfile separa development/production e o entrypoint entrega sinais com exec. Configuração fica em configs, massas/importadores em dados e testes nas aplicações.

### Consequências

- Positiva: Reduz divergência de infraestrutura e oferece comandos reproduzíveis para desenvolver e validar.
- Negativa: Exige sincronizar a cópia distribuída do toolkit com sua origem e testar mudanças transversais.
- Neutra: A cópia do pacote no repositório permite build independente; não contém código corporativo nem configuração local.

### Confirmação

Confrontar os arquivos das aplicações e da composição com os contratos F01. Exercitar os cenários reais de autorização, integridade, indisponibilidade e reinício aplicáveis. Testes e aceite humano têm evidências externas; este documento não é relatório de execução.

## Informações adicionais

A data registra a formalização deste ADR. O índice [de decisões](README.md) e o [documento arquitetural](../design/architecture.md) apontam para esta origem. Não há ADR anterior substituído.
