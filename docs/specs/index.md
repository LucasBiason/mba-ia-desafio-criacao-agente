# Especificações do Residencial Aurora

O [recorte vigente](../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa a administração manual, o assistente no portal e a API do assistente. Os contratos conservam os IDs; o modo informa em qual superfície o critério precisa ser demonstrado. A descrição de implementação não substitui execução de testes ou aceite humano.

| ID | Funcionalidade | Spec | Plano | Contrato | Etapa |
| --- | --- | --- | --- | --- | --- |
| [F01](../prd/functional/F01-fundacao.md) | Fundação executável | [Spec](F01-fundacao/spec.md) | [Plano](F01-fundacao/plan.md) | [Contrato](F01-fundacao/contract.md) | Base administrativa |
| [F02](../prd/functional/F02-apartamentos.md) | Cadastro de apartamentos | [Spec](F02-apartamentos/spec.md) | [Plano](F02-apartamentos/plan.md) | [Contrato](F02-apartamentos/contract.md) | Base administrativa |
| [F03](../prd/functional/F03-autenticacao.md) | Autenticação e autorização | [Spec](F03-autenticacao/spec.md) | [Plano](F03-autenticacao/plan.md) | [Contrato](F03-autenticacao/contract.md) | Base administrativa |
| [F04](../prd/functional/F04-usuarios.md) | Gestão de usuários e perfis | [Spec](F04-usuarios/spec.md) | [Plano](F04-usuarios/plan.md) | [Contrato](F04-usuarios/contract.md) | Base administrativa |
| [F05](../prd/functional/F05-areas.md) | Cadastro de áreas comuns | [Spec](F05-areas/spec.md) | [Plano](F05-areas/plan.md) | [Contrato](F05-areas/contract.md) | Base administrativa |
| [F06](../prd/functional/F06-regulamento.md) | Regulamento único e versionado | [Spec](F06-regulamento/spec.md) | [Plano](F06-regulamento/plan.md) | [Contrato](F06-regulamento/contract.md) | Base administrativa |
| [F07](../prd/functional/F07-reservas.md) | Reservas e agenda por área | [Spec](F07-reservas/spec.md) | [Plano](F07-reservas/plan.md) | [Contrato](F07-reservas/contract.md) | Base: consultas e horários; mutações no assistente com aceite pendente |
| [F08](../prd/functional/F08-visitantes.md) | Autorizações de visita | [Spec](F08-visitantes/spec.md) | [Plano](F08-visitantes/plan.md) | [Contrato](F08-visitantes/contract.md) | Base: consultas e horários; autorização confirmada no assistente com aceite pendente |
| [F09](../prd/functional/F09-chat-agente.md) | Chat do morador e agente | [Spec](F09-chat-agente/spec.md) | [Plano](F09-chat-agente/plan.md) | [Contrato](F09-chat-agente/contract.md) | Assistente do morador implementado; aceite humano pendente |
| [F10](../prd/functional/F10-avaliacao.md) | Compatibilidade e aceite do desafio | [Spec](F10-avaliacao/spec.md) | [Plano](F10-avaliacao/plan.md) | [Contrato](F10-avaliacao/contract.md) | API do assistente implementada; avaliação completa do candidato pendente |
| [F11](../prd/functional/F11-navegacao.md) | Navegação responsiva por perfil | [Spec](F11-navegacao/spec.md) | [Plano](F11-navegacao/plan.md) | [Contrato](F11-navegacao/contract.md) | Base administrativa |
| [F12](../prd/functional/F12-painel-administrativo.md) | Visão geral administrativa | [Spec](F12-painel-administrativo/spec.md) | [Plano](F12-painel-administrativo/plan.md) | [Contrato](F12-painel-administrativo/contract.md) | Base administrativa |
| [F13](../prd/functional/F13-painel-morador.md) | Visão geral do morador | [Spec](F13-painel-morador/spec.md) | [Plano](F13-painel-morador/plan.md) | [Contrato](F13-painel-morador/contract.md) | Consultas do morador preservadas |
| [F14](../prd/functional/F14-perfil.md) | Consulta do próprio perfil | [Spec](F14-perfil/spec.md) | [Plano](F14-perfil/plan.md) | [Contrato](F14-perfil/contract.md) | Base administrativa |

## Arquitetura compartilhada

- [Arquitetura e fluxos](../design/architecture.md).
- [Contexto e aplicações C4](../design/c4-context.md).
- [Modelo conceitual e cardinalidades](../design/data-model.md).
- [Decisões arquiteturais](../adr/README.md).
