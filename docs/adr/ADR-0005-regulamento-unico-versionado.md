---
status: accepted
date: 2026-11-18
decision-makers: [Responsável pelo produto]
source: ../design/architecture.md
source_section: "10. Decisões, riscos e validação"
feature: F06
spec: ../specs/F06-regulamento/spec.md
spec_section: "3. Decisões técnicas"
---

# ADR-0005: Manter um regulamento vigente com versões imutáveis

## Contexto e problema

A administração precisa atualizar o regulamento sem perder autoria e conteúdo anterior. O requisito define uma única regra vigente, versão zero inicial e nova versão a cada edição, sem criação paralela ou exclusão.

Origem: [arquitetura](../design/architecture.md#10-decisões-riscos-e-validação), [PRD](../prd/index.md) e [spec F06](../specs/F06-regulamento/spec.md#3-decisões-técnicas). A formalização preserva as escolhas do produto e distingue a topologia observada das decisões aprovadas.

## Fatores da decisão

Responsabilidades explícitas, segurança por recurso, preservação dos dados e operação local reproduzível. A decisão é estrutural, precisa de justificativa rastreável e tem duração superior ao detalhe de uma implementação.

## Opções consideradas

- Versões append-only com controle de concorrência, opção escolhida.
- Sobrescrever ou excluir o histórico, comportamento excluído pelo requisito.

## Resultado da decisão

Vamos publicar uma nova versão em transação, preservando conteúdo, autor e horário. O cliente envia a versão que editou; uma publicação concorrente sobre versão ultrapassada recebe conflito. A tela consulta o vigente; não oferece exclusão ou criação de outro regulamento.

### Consequências

- Positiva: Permite rastrear alterações e evita sobrescrita silenciosa de edições concorrentes.
- Negativa: O histórico cresce e as referências a contas publicadoras devem ser preservadas.
- Neutra: A busca seletiva do regulamento pelo agente será detalhada na próxima etapa.

### Confirmação

Confrontar os arquivos das aplicações e da composição com os contratos F06. Exercitar os cenários reais de autorização, integridade, indisponibilidade e reinício aplicáveis. Testes e aceite humano têm evidências externas; este documento não é relatório de execução.

## Informações adicionais

A data registra a formalização deste ADR. O índice [de decisões](README.md) e o [documento arquitetural](../design/architecture.md) apontam para esta origem. Não há ADR anterior substituído.
