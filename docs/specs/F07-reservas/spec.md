---
spec_template: 1
feature: F07
ceremony: full
prd_source: docs/prd/functional/F07-reservas.md
---

# F07 — Reservas e agenda por área

## 1. Visão técnica

A base fornece calendário administrativo por área, localização por código e edição do horário. O morador visualiza suas reservas na unidade selecionada. As operações de criar e cancelar reservas serão integradas no roteiro de agentes. Elas exigem código estável, exclusividade no armazenamento e validação de titularidade no cancelamento.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F07](../../prd/functional/F07-reservas.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.

## 2. Impacto arquitetural

O painel chama a API autenticada e usa filtros por área, data e estado. A interface do morador envia somente a unidade selecionada. A API verifica vínculo em cada leitura. O agente e as futuras tools recebem o contexto autenticado do servidor e executam regras do domínio antes de gravar.

## 3. Decisões técnicas

O calendário abre no mês atual, com seleção de todas as áreas ou de uma área. No recorte consolidado a cor identifica a área. Clicar em um dia abre a lista completa daquele dia, inclusive quando está vazio. Buscar pelo código abre a área, o mês e o dia daquele registro. Os horários de início e fim são opcionais, devem ser preenchidos juntos e respeitar a ordem no mesmo dia. O banco preparado contém o índice parcial `reservations_active_slot` para registros ativos por área e data. A futura ferramenta escreve em transação e converte a colisão desse índice em indisponibilidade. Um código já emitido permanece indisponível após cancelamento. Por consistência, escolher uma única fonte da taxa e gravar o valor usado no efeito.

## 4. Visão de componentes

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Router | services/agenda/routers/reservation_router.py | Receber DTO e identidade e chamar o controller |
| Controller | services/agenda/controllers/reservation_controller.py | Coordenar validação, persistência e serialização |
| Validator | services/agenda/validators/reservation_validator.py | Verificar permissão e regras da operação |
| Repository | services/agenda/repositories/reservation_repository.py | Consultar e escrever com SQLAlchemy em transação |
| Serializer | services/agenda/serializers/reservation_serializer.py | Produzir DTO público sem campos internos |
| Composição | services/agenda/main.py | Montar routers, middleware, Swagger e health do toolkit |

As schemas Pydantic validam tipo e formato. Validators não gravam e controllers não acessam Session ou engine. O repository aplica flush, locks e constraints conforme a operação. Falha faz rollback. A documentação OpenAPI declara os contratos de entrada, saída, erros e autenticação.

## 5. Contratos de interface

GET `/api/admin/reservations` para administração aceita `area_id`, `date` e `status` opcionais. GET `/api/resident/reservations?apartment=101` para morador; a unidade precisa pertencer à sessão autenticada do produto. A projeção inclui `code`, `apartment`, `area_id`, `area_name`, `date`, `fee_cents`, `status`, `start_time` e `end_time`. A administração recebe também `resident_id`, usado para mostrar o nome do titular. PATCH `/api/admin/reservations/{code}/hours` recebe os dois horários em `HH:MM` ou ambos nulos e devolve o registro atualizado. Aprovação e gravação no fluxo acadêmico são contratos de F09 e F10.

A API recusa unidade fora do vínculo sem expor dados. A futura disputa devolve indisponibilidade sem identificar o vencedor. Falha de persistência não confirma efeito.

## 6. Modelo de dados

Reserva identifica código, área, unidade, data, estado e taxa histórica. Dados iniciais vêm de reservas.json. Horários ausentes na origem são nulos. Ajustar os horários não libera espaço para outra reserva na mesma data e área. Quando um apartamento troca de titular, a administração preserva o histórico. A consulta do morador exige vínculo atual e titularidade do registro, sem transferir reservas. Na integração, manter registros de cancelamento ou chaves históricas equivalentes e testar unicidade também em código já cancelado. O estado ativo será protegido na mesma fronteira da gravação, com tratamento de colisão e rollback.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F07-AC01 | Base. Autenticar, selecionar a unidade e comparar a projeção com a agenda administrativa. | A consulta mostra somente reservas da unidade autorizada. |
| F07-AC02 | Integração do agente. Disparar aprovações simultâneas em duas sessões e somar projeções de ambas as unidades. | Duas aprovações retornam o contrato previsto e fica uma única reserva ativa. |
| F07-AC03 | Integração do agente. Exercitar tool de cancelamento e de criação e comparar códigos e estado antes e depois. | Cancelamento não cria pendência e o código novo difere do anterior e dos iniciais. |
| F07-AC04 | Base. Clicar em dias ocupados e vazios no mês, filtrar uma área e buscar um código de outra área. | O calendário mostra os horários e os titulares, e clicar em uma data abre a lista do dia. |
| F07-AC05 | Integração do agente. Executar as duas intenções e comparar eventos, pendências e reservas antes e depois da aprovação. | A gratuita é gravada sem pendência e a paga fica pendente até decisão pela API. |
| F07-AC06 | Base. Atualizar horários válidos, testar intervalo invertido e acesso de morador à edição, consultar a reserva pelo titular. | Administração salva início e fim em ordem e o morador titular vê os horários. |
| F07-SEC01 | Base. Consultar a API com dois vínculos distintos e comparar o corpo de recusa. | A API bloqueia acesso e o corpo não contém titular, códigos ou dados de outra unidade. |
| NFR01-AC01 | Base. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR02-AC01 | Base. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. | Efeito confirmado permanece. A falha é observável e o domínio fica consistente. |
| NFR03-AC01 | Base. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |
