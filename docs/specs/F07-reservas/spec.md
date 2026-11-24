---
spec_template: 1
feature: F07
ceremony: full
prd_source: docs/prd/functional/F07-reservas.md
---

# F07 — Reservas e agenda por área

## 1. Visão técnica

A base fornece calendário administrativo por área, localização por código e edição do horário. O morador visualiza suas reservas na unidade selecionada. No assistente, criar e cancelar são tools com isolamento de unidade e recibo baseado no resultado do domínio. Elas exigem código estável, exclusividade no armazenamento e validação de titularidade no cancelamento.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F07](../../prd/functional/F07-reservas.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

O painel chama a API autenticada e usa filtros por área, data e estado. A interface do morador envia somente a unidade selecionada. A API verifica vínculo em cada leitura. O agente e as tools recebem o contexto autenticado do servidor e executam regras do domínio antes de gravar.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0002](../../adr/ADR-0002-orm-e-integridade-transacional.md).

O calendário abre no mês atual, com seleção de todas as áreas ou de uma área. No recorte consolidado a cor identifica a área. Clicar em um dia abre a lista completa daquele dia, inclusive quando está vazio. Buscar pelo código abre a área, o mês e o dia daquele registro. Os horários de início e fim são opcionais, devem ser preenchidos juntos e respeitar a ordem no mesmo dia. O banco preparado contém o índice parcial `reservations_active_slot` para registros ativos por área e data. A ferramenta escreve em transação e converte a colisão desse índice em indisponibilidade. Um código já emitido permanece indisponível após cancelamento. Por consistência, escolher uma única fonte da taxa e gravar o valor usado no efeito.

O portal usa o [protocolo de delegação de F09](../F09-chat-agente/spec.md#protocolo-interno-de-delegação). `reserve`, `cancel` e `availability` exigem área e data validadas no servidor; o especialista não reescreve os argumentos do envelope. O executor emite resultado canônico e deduplica sua execução por turno. Reserva paga produz pendência com os detalhes originais; gratuita e cancelamento seguem suas regras sem confirmação. As constraints e o consumo único na transação continuam sendo a proteção de concorrência. A API do assistente em F10 conserva seu protocolo próprio.

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

GET `/api/admin/reservations` para administração aceita `area_id`, `date` e `status` opcionais. GET `/api/resident/reservations?apartment=101` para morador; a unidade precisa pertencer à sessão autenticada do produto. A projeção inclui `code`, `apartment`, `area_id`, `area_name`, `date`, `fee_cents`, `status`, `start_time` e `end_time`. A administração recebe também `resident_id`, usado para mostrar o nome do titular. PATCH `/api/admin/reservations/{code}/hours` recebe os dois horários em `HH:MM` ou ambos nulos e devolve o registro atualizado. Aprovação e gravação no fluxo do assistente são contratos de F09 e F10.

A API recusa unidade fora do vínculo sem expor dados. A disputa devolve indisponibilidade sem identificar o vencedor. Falha de persistência não confirma efeito.

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
| NFR01-AC01 | Base: HTTP real. Dado 9101 pertence a QA_A e 9102 a QA_B; quando consultar GET /api/resident/reservations?apartment=9102 com QA_A. | Então HTTP 403 APARTMENT_FORBIDDEN, sem reservas, códigos ou titular de 9102. |
| NFR02-AC01 | Integração do agente: HTTP e banco reais. Dado Duas sessões autorizadas disputam a mesma QA_AREA paga na data QA_DAY livre; quando gerar duas pendências pelo protocolo delegar_solicitacao com operation=reserve e executar_reserva_validada e aprová-las simultaneamente; consultar a agenda e repetir a decisão vencedora. | Então existe exatamente uma reserva ativa para área/data, a outra execução informa indisponibilidade e reenvio sequencial retorna 409 sem segundo efeito. |
| NFR03-AC01 | Base: HTTP real. Dado Há uma reserva QA_RES_A de QA_A/9101 e QA_RES_B de QA_B/9102; quando consultar GET /api/resident/reservations?apartment=9101 com QA_A e inspecionar o corpo. | Então apenas QA_RES_A é retornada; não há QA_RES_B, resident_id alheio, bearer nem segredo. |

Nomes de áreas são resolvidos no catálogo por ID ou nome completo normalizado. Uma abreviação por palavras iniciais, como “salão”, só identifica uma área quando há exatamente uma correspondência. Nomes ambíguos ou inexistentes não permitem reservar nem cancelar.
