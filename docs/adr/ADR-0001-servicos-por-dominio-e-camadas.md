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

# ADR-0001: Separar os serviços por domínio e aplicar camadas

## Contexto e problema

A base concentra dados sensíveis e operações com regras diferentes. O recorte de serviços e o fluxo router → controller → validators → repository → serializer foram definidos como padrão do produto; um módulo genérico de domínio não representa esse recorte.

Origem: [arquitetura](../design/architecture.md#10-decisões-riscos-e-validação), [PRD](../prd/index.md) e [spec F01](../specs/F01-fundacao/spec.md#3-decisões-técnicas). A formalização preserva as escolhas do produto e distingue a topologia observada das decisões aprovadas.

## Fatores da decisão

Responsabilidades explícitas, segurança por recurso, preservação dos dados e operação local reproduzível. A decisão é estrutural, precisa de justificativa rastreável e tem duração superior ao detalhe de uma implementação.

## Opções consideradas

- Serviços por domínio e camadas explícitas, opção escolhida.
- Serviço agregado sem fronteiras por domínio: opção não adotada.

## Resultado da decisão

Vamos separar autenticação, usuários, apartamentos, áreas, agenda, visitas, configurações e fronteira do agente em aplicações próprias. O padrão inclui a API pública do desafio, sem exceção de camadas: cada aplicação mantém composição mínima, validação de permissão e regra no validator, coordenação no controller, persistência no repository e serialização explícita.

### Consequências

- Positiva: Torna a responsabilidade e a autorização de cada operação verificáveis.
- Negativa: Aumenta processos, configurações e dependências entre serviços; exige contratos estáveis e correlação.
- Neutra: A divisão lógica não equivale a banco fisicamente isolado; essa questão está no ADR-0006.

### Confirmação

Confrontar os arquivos das aplicações e da composição com os contratos F01. Exercitar os cenários reais de autorização, integridade, indisponibilidade e reinício aplicáveis. Testes e aceite humano têm evidências externas; este documento não é relatório de execução.

## Informações adicionais

A data registra a formalização deste ADR. O índice [de decisões](README.md) e o [documento arquitetural](../design/architecture.md) apontam para esta origem. Não há ADR anterior substituído.
