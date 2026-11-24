---
status: accepted
date: 2026-11-18
decision-makers: [Responsável pelo produto]
source: ../design/architecture.md
source_section: "10. Decisões, riscos e validação"
feature: F03
spec: ../specs/F03-autenticacao/spec.md
spec_section: "3. Decisões técnicas"
---

# ADR-0003: Centralizar identidade JWT e autorizar por recurso

## Contexto e problema

As APIs privadas precisam conhecer a conta autenticada, seu papel e seus vínculos atuais. O contexto não pode ser escolhido pelo corpo da requisição. O produto define JWT nos headers e verificação central de sessão.

Origem: [arquitetura](../design/architecture.md#10-decisões-riscos-e-validação), [PRD](../prd/index.md) e [spec F03](../specs/F03-autenticacao/spec.md#3-decisões-técnicas). A formalização preserva as escolhas do produto e distingue a topologia observada das decisões aprovadas.

## Fatores da decisão

Responsabilidades explícitas, segurança por recurso, preservação dos dados e operação local reproduzível. A decisão é estrutural, precisa de justificativa rastreável e tem duração superior ao detalhe de uma implementação.

## Opções consideradas

- JWT com sessão revogável e introspecção central, opção definida no produto; não houve comparação formal de outros protocolos.

## Resultado da decisão

Vamos autenticar com JWT, verificar sessão ativa na autoridade de identidade e autorizar ação e recurso nos validators. Middleware autentica; o papel e o vínculo efetivos vêm do servidor. Falha de introspecção recusa a operação, mudança de senha/estado revoga sessões e logout invalida a sessão no servidor.

### Consequências

- Positiva: Revogação e mudanças de acesso produzem efeito nas APIs dependentes.
- Negativa: A disponibilidade da identidade condiciona as operações privadas e adiciona uma chamada interna.
- Neutra: O esquema do produto expõe admin e resident. O bootstrap cria estruturas ausentes e as contas iniciais de um banco novo; não executa conversão de papéis ou alteração de schema existente.

### Confirmação

Confrontar os arquivos das aplicações e da composição com os contratos F03. Exercitar os cenários reais de autorização, integridade, indisponibilidade e reinício aplicáveis. Testes e aceite humano têm evidências externas; este documento não é relatório de execução.

## Informações adicionais

A data registra a formalização deste ADR. O índice [de decisões](README.md) e o [documento arquitetural](../design/architecture.md) apontam para esta origem. Não há ADR anterior substituído.
