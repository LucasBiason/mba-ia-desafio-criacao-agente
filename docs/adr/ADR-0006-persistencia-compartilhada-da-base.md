---
status: proposed
date: 2026-11-18
decision-makers: [Responsável pelo produto]
source: ../design/architecture.md
source_section: "10. Decisões, riscos e validação"
feature: F01
spec: ../specs/F01-fundacao/spec.md
spec_section: "3. Decisões técnicas"
---

# ADR-0006: Preservar provisoriamente os dois bancos da base

## Contexto e problema

A implementação atual usa PostgreSQL de identidade para auth/users e PostgreSQL de condomínio para os demais serviços. Esse arranjo preservou IDs, constraints e dados na refatoração. Não há decisão específica aprovada sobre isolamento físico por serviço; este registro retroativo permanece proposto.

Origem: [arquitetura](../design/architecture.md#10-decisões-riscos-e-validação), [PRD](../prd/index.md) e [spec F01](../specs/F01-fundacao/spec.md#3-decisões-técnicas). A formalização preserva as escolhas do produto e distingue a topologia observada das decisões aprovadas.

## Fatores da decisão

Responsabilidades explícitas, segurança por recurso, preservação dos dados e operação local reproduzível. A decisão é estrutural, precisa de justificativa rastreável e tem duração superior ao detalhe de uma implementação.

## Opções consideradas

- Dois bancos compartilhados, arranjo atualmente implementado a confirmar.
- Bancos físicos por domínio, alternativa para análise futura com contratos e migração próprios.

## Resultado da decisão

A proposta é manter os dois bancos na base local enquanto se valida o produto, com repositories por domínio e relações documentadas. Não considerar a separação física resolvida por existirem processos distintos. Uma alteração futura exige aprovação, migração preservando dados e novo ADR que substitua este registro.

### Consequências

- Positiva: Preserva a base existente e suas constraints durante o fechamento funcional.
- Negativa: Mantém acoplamento de esquema e compartilhamento de disponibilidade; os serviços não têm autonomia física de dados.
- Neutra: O estado proposed não impede descrever a topologia existente nem a transforma em decisão aceita.

### Confirmação

Confrontar os arquivos das aplicações e da composição com os contratos F01. Exercitar os cenários reais de autorização, integridade, indisponibilidade e reinício aplicáveis. Testes e aceite humano têm evidências externas; este documento não é relatório de execução.

## Informações adicionais

A data registra a formalização deste ADR. O índice [de decisões](README.md) e o [documento arquitetural](../design/architecture.md) apontam para esta origem. Não há ADR anterior substituído.
