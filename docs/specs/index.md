# Especificações do Residencial Aurora

O [PRD](../prd/index.md) dá os requisitos de produto. Cada spec vincula critérios, planos e procedimentos de prova. O contrato é uma expectativa a verificar. Os resultados realmente observados ficam no [registro de validação](../validacao.md).

| Requisito | Funcionalidade | Spec | Plano | Contrato | Etapa |
| --- | --- | --- | --- | --- | --- |
| FR01 → [F01](../prd/functional/F01-fundacao.md) | Fundação executável | [Spec](F01-fundacao/spec.md) | [Plano](F01-fundacao/plan.md) | [Contrato](F01-fundacao/contract.md) | Base |
| FR02 → [F02](../prd/functional/F02-apartamentos.md) | Cadastro de apartamentos | [Spec](F02-apartamentos/spec.md) | [Plano](F02-apartamentos/plan.md) | [Contrato](F02-apartamentos/contract.md) | Base |
| FR03 → [F03](../prd/functional/F03-autenticacao.md) | Autenticação e autorização | [Spec](F03-autenticacao/spec.md) | [Plano](F03-autenticacao/plan.md) | [Contrato](F03-autenticacao/contract.md) | Base |
| FR04 → [F04](../prd/functional/F04-usuarios.md) | Gestão de usuários e perfis | [Spec](F04-usuarios/spec.md) | [Plano](F04-usuarios/plan.md) | [Contrato](F04-usuarios/contract.md) | Base |
| FR05 → [F05](../prd/functional/F05-areas.md) | Cadastro de áreas comuns | [Spec](F05-areas/spec.md) | [Plano](F05-areas/plan.md) | [Contrato](F05-areas/contract.md) | Base |
| FR06 → [F06](../prd/functional/F06-regulamento.md) | Regulamento único e versionado | [Spec](F06-regulamento/spec.md) | [Plano](F06-regulamento/plan.md) | [Contrato](F06-regulamento/contract.md) | Base |
| FR07 → [F07](../prd/functional/F07-reservas.md) | Reservas e agenda por área | [Spec](F07-reservas/spec.md) | [Plano](F07-reservas/plan.md) | [Contrato](F07-reservas/contract.md) | Base e aula do agente |
| FR08 → [F08](../prd/functional/F08-visitantes.md) | Autorizações de visita | [Spec](F08-visitantes/spec.md) | [Plano](F08-visitantes/plan.md) | [Contrato](F08-visitantes/contract.md) | Base e aula do agente |
| FR09 → [F09](../prd/functional/F09-chat-agente.md) | Chat do morador e agente | [Spec](F09-chat-agente/spec.md) | [Plano](F09-chat-agente/plan.md) | [Contrato](F09-chat-agente/contract.md) | Base e aula do agente |
| FR10 → [F10](../prd/functional/F10-avaliacao.md) | Compatibilidade e aceite acadêmico | [Spec](F10-avaliacao/spec.md) | [Plano](F10-avaliacao/plan.md) | [Contrato](F10-avaliacao/contract.md) | Base e avaliação acadêmica |

A consulta e a mutação são verificadas em etapas diferentes nas features F07 e F08. F09 entrega o acesso e a sessão do chat na base. Orquestração, tools e protocolo acadêmico seguem o [roteiro acompanhado](../roteiro-agente.md).

## Leitura recomendada

1. [Arquitetura e fluxo do produto](../arquitetura.md)
2. [Telas, navegação e design system](../telas.md)
3. [Roteiro do agente por etapas](../roteiro-agente.md)
4. [Validação e limites da entrega](../validacao.md)

- **F11 — Navegação responsiva por perfil** · [Requisito](../prd/functional/F11-navegacao.md) · [Spec](F11-navegacao/spec.md) · [Plano](F11-navegacao/plan.md) · [Contrato](F11-navegacao/contract.md). Implementação existente, aceite e integração pendentes.

- **F12 — Visão geral administrativa** · [Requisito](../prd/functional/F12-painel-administrativo.md) · [Spec](F12-painel-administrativo/spec.md) · [Plano](F12-painel-administrativo/plan.md) · [Contrato](F12-painel-administrativo/contract.md). Implementação existente, aceite e integração pendentes.

- **F13 — Visão geral do morador** · [Requisito](../prd/functional/F13-painel-morador.md) · [Spec](F13-painel-morador/spec.md) · [Plano](F13-painel-morador/plan.md) · [Contrato](F13-painel-morador/contract.md). Implementação existente, aceite e integração pendentes.

- **F14 — Consulta do próprio perfil** · [Requisito](../prd/functional/F14-perfil.md) · [Spec](F14-perfil/spec.md) · [Plano](F14-perfil/plan.md) · [Contrato](F14-perfil/contract.md). Implementação existente, aceite e integração pendentes.

A [matriz da primeira entrega](../entrega-01.md) é a referência de situação do pacote. A documentação foi reconciliada retrospectivamente com o código. A ordem histórica sdd-spec → sdd-implement → sdd-evaluate exige registros de execução que não foram localizados nesta revisão.
