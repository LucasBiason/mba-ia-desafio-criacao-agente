---
spec_template: 1
feature: F08
ceremony: full
prd_source: docs/prd/functional/F08-visitantes.md
---

# F08 — Autorizações de visita

## 1. Visão técnica

A base importa autorizações de visita. A administração registra horários de entrada e saída e o morador pode consultá-los para suas autorizações. A liberação nova exige confirmação externa à conversa. A autorização representa permissão para data futura e é distinta de comparecimento.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F08](../../prd/functional/F08-visitantes.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../arquitetura.md). Este documento especifica os contratos da base e das etapas da aula identificadas na matriz.

## 2. Impacto arquitetural

Consulta de visitante chega a `condo` e combina identidade com vínculo. A aula liga a ação de visitante à mesma infraestrutura de confirmações de reservas pagas. Uma ação pendente carrega somente o nome, a data e o apartamento já validado.

## 3. Decisões técnicas

A edição administrativa atualiza apenas os horários de uma autorização existente. Entrada pode ser informada sem saída. Se houver saída, deve ser posterior à entrada no mesmo dia. O chat futuro pode pedir nome e data e propor autorização; o código persiste após decisão válida na rota. Atualizar estado e consumir a pendência uma única vez com fronteira consistente de falha e rollback.

## 4. Visão de componentes

- Visualização de autorizações administrativas e da unidade do morador.
- API de projeções baseada em fixture e armazenamento do domínio.
- Prática futura: especialista de visitantes e ação validada com o serviço de confirmações.

## 5. Contratos de interface

GET `/api/admin/visits` para administração aceita filtros opcionais `apartment` e `date`. GET `/api/resident/visits?apartment=101` para morador com vínculo. A projeção fornece `id`, `apartment`, `name`, `date`, `entry_time` e `exit_time`. PATCH `/api/admin/visits/{id}/hours` recebe um ou os dois horários em `HH:MM` ou nulo. Campos omitidos mantêm o valor atual e a resposta devolve a autorização atualizada. A confirmação acadêmica prevista em F10 usa a coleção `confirmacoes_pendentes` e a rota correspondente.

Data ou nome inválido pede correção. A consulta rejeita unidade alheia sem revelar registros. Na aula, recusa ou falha de execução impede novo efeito.

## 6. Modelo de dados

Autorização persiste id, unidade, nome, data, titularidade e horários opcionais. A base importa visitantes.json e mantém nulos os horários ausentes da fonte. A consulta do morador exige vínculo atual e titularidade do registro, sem transferir autorizações ao trocar o responsável. Na aula, decisão negada não cria registro, e cada aprovação válida cria uma autorização para a unidade vinculada à sessão.

## 7. Estratégia de testes

O [contrato](contract.md) organiza as verificações por critério. Use credenciais locais e massa descartável. **Base** é o comportamento especificado para a aplicação preparada. **Aula do agente** e **Avaliação acadêmica** identificam os testes das etapas guiadas. O [registro de validação](../../validacao.md) indica quais verificações foram de fato executadas.

| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F08-AC01 | Aula do agente. Capturar eventos e consultar antes e depois de responder a pendência pela API. | A resposta cria pendência e a autorização só aparece após aprovação pela rota. |
| F08-AC02 | Aula do agente. Criar, parar e iniciar sem restaurar, e comparar nome e data na projeção autorizada. | Após reinício a autorização segue consultável para a unidade correta. |
| F08-AC03 | Aula do agente. Consultar com a sessão inicial usando outro número na mensagem e inspecionar eventos e estado. | Resposta e eventos não incluem nomes ou autorizações de outra unidade. |
| F08-AC04 | Base. Entrar pelos dois papéis, comparar a lista e validar unidade ativa, vazio e recusa fora do vínculo. | Administração consulta as autorizações e o morador vê somente a própria unidade. |
| F08-AC05 | Base. Gravar entrada e saída, testar saída sem entrada e comparar a autorização antes e depois. | Administração registra entrada e saída, e a projeção exibe os valores preservando a data e a unidade. |
| F08-SEC01 | Base. Variar a unidade enviada, inspecionar o corpo de recusa e a projeção legítima. | A rota rejeita o acesso e o JSON não revela registros pessoais. |
| NFR01-AC01 | Base. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR02-AC01 | Base. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. | Efeito confirmado permanece. A falha é observável e o domínio fica consistente. |
| NFR03-AC01 | Base. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |

### Situação da execução

Parcial. Consulta por papel e registro de entrada e saída. Fonte do código: `services/domain/app.py; web/src/records.jsx`. As evidências disponíveis são tests/test_api.py — horários e escopo; novas autorizações confirmadas pendentes. Esta revisão é retrospectiva e não atesta a ordem histórica de invocação das skills. Critérios de aula e avaliação continuam pendentes. A [entrega](../../entrega-01.md) concentra o fechamento.

Revisão das fontes: índice atualizado com F11–F14 conferido; IDs e dependências de domínio anteriores preservados.

Conferência final: comportamentos do requisito vinculados aos procedimentos de aceite e situação da primeira entrega.
