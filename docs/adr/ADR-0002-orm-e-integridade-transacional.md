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

# ADR-0002: Persistir por ORM com integridade na transação

## Contexto e problema

Uma validação anterior à gravação pode se tornar inválida diante de outra requisição. O padrão solicitado usa ORM nos repositories e reserva SQL textual de aplicação a consultas que demonstrem necessidade.

Origem: [arquitetura](../design/architecture.md#10-decisões-riscos-e-validação), [PRD](../prd/index.md) e [spec F01](../specs/F01-fundacao/spec.md#3-decisões-técnicas). A formalização preserva as escolhas do produto e distingue a topologia observada das decisões aprovadas.

## Fatores da decisão

Responsabilidades explícitas, segurança por recurso, preservação dos dados e operação local reproduzível. A decisão é estrutural, precisa de justificativa rastreável e tem duração superior ao detalhe de uma implementação.

## Opções consideradas

- SQLAlchemy ORM para consultas e mutações, opção escolhida.
- INSERT/UPDATE/DELETE textuais nos casos de uso, forma rejeitada pelo padrão do produto.

## Resultado da decisão

Vamos usar SQLAlchemy e limitar o acesso ao banco aos repositories. Transações, constraints e locks protegem a gravação; exceções fazem rollback. DDL de migração é separado de CRUD. A exclusividade de reserva ativa por área/data permanece no armazenamento; uma fila futura não substitui essa garantia.

### Consequências

- Positiva: Preserva integridade sob concorrência e mantém a implementação alinhada às camadas.
- Negativa: Exige tratar colisões e transações explicitamente; a validação de formulário não basta.
- Neutra: Não escolhe fila, broker, worker ou protocolo de confirmação do agente.

### Confirmação

Confrontar os arquivos das aplicações e da composição com os contratos F01. Exercitar os cenários reais de autorização, integridade, indisponibilidade e reinício aplicáveis. Testes e aceite humano têm evidências externas; este documento não é relatório de execução.

## Informações adicionais

A data registra a formalização deste ADR. O índice [de decisões](README.md) e o [documento arquitetural](../design/architecture.md) apontam para esta origem. Não há ADR anterior substituído.
