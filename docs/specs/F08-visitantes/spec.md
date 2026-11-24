---
spec_template: 1
feature: F08
ceremony: full
prd_source: docs/prd/functional/F08-visitantes.md
---

# F08 — Autorizações de visita

## 1. Visão técnica

A base importa autorizações de visita. A administração registra horários de entrada e saída e o morador pode consultá-los para suas autorizações. A liberação nova exige confirmação externa à conversa. A autorização representa permissão para data futura e é distinta de comparecimento.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F08](../../prd/functional/F08-visitantes.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

Consulta de visitante chega a `visits` e combina identidade com vínculo. O agente liga a ação de visitante à mesma infraestrutura de confirmações de reservas pagas. Uma ação pendente carrega somente o nome, a data e o apartamento já validado.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0002](../../adr/ADR-0002-orm-e-integridade-transacional.md), [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

A proposta de visita segue a [delegação tipada do portal](../F09-chat-agente/spec.md#protocolo-interno-de-delegação) e o [ADR-0009](../../adr/ADR-0009-delegacao-tipada-e-recibos-do-servidor.md). O principal extrai nome e data do pedido atual; o servidor valida explicitamente o DTO e calcula o especialista de convivência. A ferramenta sem argumentos executa somente o envelope validado daquele turno. Identidade, unidade e elegibilidade são revalidadas pelo domínio.

Nome e data válidos produzem uma pendência durável, com os detalhes originais, antes de responder ao morador. Uma confirmação verbal na mesma mensagem não aprova a visita. A rota humana recupera os argumentos da pendência; negar não cria autorização e aprovar consome o ID uma única vez. Repetir a ferramenta no mesmo turno conserva a proposta original; não gera outro UUID nem nova autorização. Histórico antigo, inclusive recusas do assistente, não concede nem retira permissão.

A edição administrativa atualiza apenas os horários de uma autorização existente. Entrada pode ser informada sem saída. Se houver saída, deve ser posterior à entrada no mesmo dia. O chat pode pedir nome e data e propor autorização; o código persiste após decisão válida na rota. Atualizar estado e consumir a pendência uma única vez com fronteira consistente de falha e rollback.

## 4. Visão de componentes

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Router | services/visits/routers/visit_router.py | Receber DTO e identidade e chamar o controller |
| Controller | services/visits/controllers/visit_controller.py | Coordenar validação, persistência e serialização |
| Validator | services/visits/validators/visit_validator.py | Verificar permissão e regras da operação |
| Repository | services/visits/repositories/visit_repository.py | Consultar e escrever com SQLAlchemy em transação |
| Serializer | services/visits/serializers/visit_serializer.py | Produzir DTO público sem campos internos |
| Composição | services/visits/main.py | Montar routers, middleware, Swagger e health do toolkit |

As schemas Pydantic validam tipo e formato. Validators não gravam e controllers não acessam Session ou engine. O repository aplica flush, locks e constraints conforme a operação. Falha faz rollback. A documentação OpenAPI declara os contratos de entrada, saída, erros e autenticação.

## 5. Contratos de interface

GET `/api/admin/visits` para administração aceita filtros opcionais `apartment` e `date`. GET `/api/resident/visits?apartment=101` para morador com vínculo. A projeção fornece `id`, `apartment`, `name`, `date`, `entry_time` e `exit_time`. PATCH `/api/admin/visits/{id}/hours` recebe um ou os dois horários em `HH:MM` ou nulo. Campos omitidos mantêm o valor atual e a resposta devolve a autorização atualizada. A confirmação do portal prevista em F09 usa a coleção `confirmacoes_pendentes` e a rota correspondente.

Data ou nome inválido pede correção canônica sem pendência nem autorização. Ausência ou violação da chamada de ferramenta exigida é indisponibilidade de protocolo, sem efeito e sem falsa recusa de permissão. O recibo público deriva da execução do servidor; uma falha de geração posterior não repete a operação. A consulta rejeita unidade alheia sem revelar registros. Na integração, recusa ou falha de execução impede novo efeito.

## 6. Modelo de dados

Autorização persiste id, unidade, nome, data, titularidade e horários opcionais. A base importa visitantes.json e mantém nulos os horários ausentes da fonte. A consulta do morador exige vínculo atual e titularidade do registro, sem transferir autorizações ao trocar o responsável. Na integração, decisão negada não cria registro, e cada aprovação válida cria uma autorização para a unidade vinculada à sessão.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F08-AC01 | Integração do agente. Capturar eventos e consultar antes e depois de responder a pendência pela API. | A resposta cria pendência e a autorização só aparece após aprovação pela rota. |
| F08-AC02 | Integração do agente. Criar, parar e iniciar sem restaurar, e comparar nome e data na projeção autorizada. | Após reinício a autorização segue consultável para a unidade correta. |
| F08-AC03 | Integração do agente. Consultar com a sessão inicial usando outro número na mensagem e inspecionar eventos e estado. | Resposta e eventos não incluem nomes ou autorizações de outra unidade. |
| F08-AC04 | Base. Entrar pelos dois papéis, comparar a lista e validar unidade ativa, vazio e recusa fora do vínculo. | Administração consulta as autorizações e o morador vê somente a própria unidade. |
| F08-AC05 | Base. Gravar entrada e saída, testar saída sem entrada e comparar a autorização antes e depois. | Administração registra entrada e saída, e a projeção exibe os valores preservando a data e a unidade. |
| F08-SEC01 | Base. Variar a unidade enviada, inspecionar o corpo de recusa e a projeção legítima. | A rota rejeita o acesso e o JSON não revela registros pessoais. |
| NFR01-AC01 | Base: HTTP real. Dado 9101 pertence a QA_A e 9102 a QA_B; quando consultar GET /api/resident/visits?apartment=9102 com QA_A. | Então HTTP 403 APARTMENT_FORBIDDEN e nenhum nome, horário ou autorização de 9102. |
| NFR02-AC01 | Integração do agente: HTTP real e reinício. Dado QA_VISIT é uma autorização sintética confirmada para QA_A/9101; quando reiniciar visits e agent sem restore e consultar GET /api/resident/visits?apartment=9101 com QA_A. | Então a autorização conserva id, nome, data e horários e não aparece duplicada. |
| NFR03-AC01 | Base: HTTP real. Dado QA_VISIT_A pertence a QA_A/9101 e QA_VISIT_B a QA_B/9102; quando consultar GET /api/resident/visits?apartment=9101 com QA_A. | Então a lista contém apenas a visita do titular autorizado, sem nome ou id de QA_VISIT_B e sem credenciais. |
