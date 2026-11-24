---
spec_template: 1
feature: F09
ceremony: full
prd_source: docs/prd/functional/F09-chat-agente.md
---

# F09 — Chat do morador e agente

## 1. Visão técnica

A base permite abrir e retomar sessões pelo perfil morador. A tela informa a indisponibilidade do assistente quando o agente não está configurado. O principal encaminha a especialistas e tools de domínio na configuração do cluster. Consultas de agenda e dúvidas de regulamento são distintas. A UI projeta reservas em lista, limpa a mensagem enviada imediatamente e mantém o novo rascunho durante a resposta.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F09](../../prd/functional/F09-chat-agente.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

O frontend envia mensagens à API autenticada. A API encaminha à fronteira privada do serviço de agente somente depois de autorizar usuário e unidade. O contexto de identidade vem do servidor, e o especialista usa portas de domínio para consultar e registrar efeitos. A interface do assistente usa um adaptador isolado para o contexto inicial fornecido pelo avaliador.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0001](../../adr/ADR-0001-servicos-por-dominio-e-camadas.md), [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md), [ADR-0004](../../adr/ADR-0004-toolkit-e-operacao-dos-servicos.md).

Preservar a sessão com unidade escolhida na abertura; mudar a unidade inicia outra sessão. O principal extrai uma delegação tipada; o servidor determina o especialista de reservas ou convivência na mesma sessão ADK. O contexto de interpretação privilegia o pedido atual e fatos canônicos autorizados, preservando todos os eventos persistidos. Convivência usa ferramentas de visitas e de regulamento. O modelo Gemini é configurado por ambiente. Tratar entrada de conversa como intenção e aplicar regras no domínio.

As tools operam no contexto verificado da sessão. Cada apartamento tem até um responsável cadastrado como usuário `resident`. Para este escopo ele é também o proprietário. Outros ocupantes ficam fora do cadastro. A tool recebe do servidor a identidade do morador e a unidade selecionada e usa ambas para verificar vínculo e titularidade. Horários presentes nas projeções ajudam a responder consultas. A reserva continua exclusiva por área e dia.

## 4. Visão de componentes

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Router | services/agent/routers/chat_router.py | Receber DTO e identidade e chamar o controller |
| Controller | services/agent/controllers/chat_controller.py | Coordenar validação, persistência e serialização |
| Validator | services/agent/validators/chat_validator.py | Verificar permissão e regras da operação |
| Repository | services/agent/repositories/chat_repository.py | Consultar e escrever com SQLAlchemy em transação |
| Serializer | services/agent/serializers/chat_serializer.py | Produzir DTO público sem campos internos |
| Composição | services/agent/main.py | Montar routers, middleware, Swagger e health do toolkit |

As schemas Pydantic validam tipo e formato. Validators não gravam e controllers não acessam Session ou engine. O repository aplica flush, locks e constraints conforme a operação. Falha faz rollback. A documentação OpenAPI declara os contratos de entrada, saída, erros e autenticação.

## 5. Contratos de interface

Todas as rotas públicas exigem `Authorization: Bearer <JWT>`, papel resident, dono da sessão e vínculo atual com a unidade. `session_id` é UUID e nunca vem da identidade escolhida pelo modelo. A superfície privada `/internal/chat/messages` exige `X-Aurora-Internal-Token`; o servidor reconstrói `user_id`, `apartment` e `session_id` e revalida esse vínculo antes de executar. A documentação Swagger representa as credenciais de cada fronteira.

| Método e rota | Entrada | Sucesso e efeito | Critérios |
| --- | --- | --- | --- |
| POST `/api/resident/chat/sessions` | `{apartment: string}` de unidade vinculada | 201 `ChatRead`; abre ou retoma a sessão canônica própria da unidade | F09-AC01, F09-AC02, F09-AC05 |
| GET `/api/resident/chat/sessions` | Bearer corrente | 200 `ChatRead[]` das sessões próprias ainda autorizadas | F09-SEC01 |
| GET `/api/resident/chat/sessions/{session_id}` | UUID no path | 200 `ChatRead` | F09-AC05, F09-SEC01 |
| POST `/api/resident/chat/sessions/{session_id}/messages` | `{message: string}` após trim, 1–2000 caracteres | 200 `MessageReply`; executa consulta ou proposta sob a unidade fixa | F09-AC01, F09-AC04 |
| GET `/api/resident/chat/sessions/{session_id}/history` | `limit` inteiro 1–100, default 50; `before` cursor opaco com até 512 caracteres; `include_archived` boolean default false | 200 `HistoryRead`; página cronológica de mensagens públicas e recibos autorizados da mesma unidade | F09-AC03, F09-AC05, F09-AC06 |
| POST `/api/resident/chat/sessions/{session_id}/archive` | Sem body de ação | 200 `ArchiveRead` com archived=true; aplica corte reversível de exibição | F09-AC06 |
| POST `/api/resident/chat/sessions/{session_id}/restore` | Sem body de ação | 200 `ArchiveRead` com archived=false; remove o corte sem apagar registros | F09-AC06 |
| POST `/api/resident/chat/sessions/{session_id}/confirmations` | `{id: UUID, confirmado: boolean estrito}`; chaves extras recusadas | 200 `MessageReply`; decide o item persistido na sessão de origem | F09-AC03, F09-SEC01 |
| POST `/internal/chat/messages` | `{session_id: string 1–80, apartment: string 1–32, user_id: string 1–80, message: string 1–2000}`; campos extras recusados | 200 `MessageReply`; somente chamada interna autenticada e contexto revalidado | F09-AC01, F09-SEC01 |

A rota de confirmação é registrada somente com agente e ações habilitados. Com `AURORA_RESIDENT_ACTIONS=0`, o runtime permanece de consulta. Recibos e propostas pendentes continuam legíveis mesmo com modelo desativado; `actions_enabled=false` faz a UI conservar os cartões e desabilitar Aprovar/Negar. As rotas de sessão e histórico continuam disponíveis com `AURORA_AGENT_ENABLED=0`; enviar mensagem nesse modo retorna 503 AGENT_NOT_CONFIGURED e não bloqueia o compositor na carga da página.

### Protocolo interno de delegação

Este protocolo pertence ao portal autenticado; as seis rotas da API do assistente em F10 conservam seu contrato. O [ADR-0009](../../adr/ADR-0009-delegacao-tipada-e-recibos-do-servidor.md) registra a fronteira entre interpretação e execução. ADK 2.14.1, google-genai e Pydantic são as dependências existentes; nenhuma biblioteca ou configuração adicional é necessária.

O principal usa chamada obrigatória `delegar_solicitacao(operation, area, date, name, question)`. O servidor valida explicitamente `DelegatedRequest`, rejeita campos de autoridade e aplica as exigências de cada operação. O schema de ferramenta enviado ao modelo não substitui essa validação. O contrato de ferramenta declara os campos de negócio como opcionais para todas as operações. O servidor valida primeiro o enum, os tipos estritos de todos os campos recebidos e a ausência de chaves desconhecidas. Em seguida, projeta somente os campos pertinentes à operação escolhida no envelope imutável. Uma indicação conhecida e tipada, como `area` em uma consulta de `regulation`, é descartada; não altera a operação, o destino ou a identidade. Campos de autoridade, chaves desconhecidas e tipos inválidos continuam sendo violações de protocolo, inclusive em campos não utilizados. A identidade e a unidade não são argumentos do modelo. O mapa fixo é:

| operation | Campos de negócio | Destino e executor |
| --- | --- | --- |
| `read_reservations` | nenhum | reservas / `executar_reserva_validada()` |
| `availability` | area e date | reservas / `executar_reserva_validada()` |
| `reserve` | area e date | reservas / `executar_reserva_validada()` |
| `cancel` | area e date | reservas / `executar_reserva_validada()` |
| `read_visitors` | nenhum | convivencia / `executar_convivencia_validada()` |
| `propose_visit` | name e date | convivencia / `executar_convivencia_validada()` |
| `regulation` | question específica | convivencia / `executar_convivencia_validada()` |
| `clarify` | question com os dados ausentes | resposta canônica sem operação de domínio |

O extrator recebe a mensagem atual e o contexto canônico autorizado. Respostas antigas do assistente não são fonte de política, papel ou aprovação; o transcript persistido permanece intacto. Referências dependem de fatos autorizados identificáveis, sem reutilizar argumentos de outra invocação. Não há operação de aprovação no enum.

Após uma única delegação válida, o servidor cria um envelope imutável vinculado ao turno, à sessão e ao especialista e define a transferência pela API pública de ações ADK. Não usa destino ou nome de handler escolhido pelo modelo. Cada filho admite somente seu executor sem argumentos, que verifica novamente o vínculo do envelope e chama a porta de domínio permitida. Transferência direta, filho incorreto, envelope ausente ou de outro turno e argumentos extras não executam negócio. O modo somente leitura exclui operações de escrita.

Chamadas duplicadas ou paralelas do executor retornam o mesmo resultado do turno. Propostas usam uma chave estável gerada pelo servidor e o ID existente do ledger: mesmo escopo/ação/payload recupera a mesma pendência; conteúdo divergente conflita. Não há migração ou DDL no servidor HTTP, nem transação de banco mantida durante chamada ao modelo. Exclusividade de reserva e consumo de confirmação continuam protegidos no repository transacional.

O backend produz `MessageReply` a partir do resultado efetivamente retornado pela porta e do ledger. Não publica JSON de delegação, argumentos internos ou prosa de permissão inventada pelo modelo. Falha de validação registra diagnóstico com nomes de campos permitidos e categorias de erro, sem valores, texto da conversa, credenciais ou argumentos brutos. Falha ou ausência de chamada exigida retorna 503 `AGENT_UNAVAILABLE`, sem sucesso aparente; dados insuficientes produzem esclarecimento canônico sem efeito. Um resultado já confirmado pelo domínio prevalece sobre falha de geração posterior. Recibos são reconhecidos pela projeção de histórico, com o mesmo filtro de privacidade dos nomes anteriores de tools.

### Schemas públicos

Os models estão em [services/agent/schemas](../../../services/agent/schemas). Datas usam AAAA-MM-DD e instantes usam ISO 8601 com fuso. Campos opcionais nulos são omitidos nas respostas que usam `response_model_exclude_none`; consumidores devem aceitar ausência além de null.

| Schema | Campos públicos |
| --- | --- |
| `ChatRead` | `id: UUID`, `apartment: string`, `created_at: datetime`, `status: awaiting_agent`. O status não certifica acesso ao provedor. |
| `MessageReply` | `message: string` obrigatório; opcionais `confirmacoes_pendentes: PendingConfirmation[]`, `resultado: ActionResult`, `history_saved: boolean`, `pending_refresh_failed: boolean`. |
| `PendingConfirmation` | `id: string`, `acao: reservar_area ou autorizar_visitante`, `detalhes: ConfirmationDetails`; opcionais `session_id` e `sourceSessionId` identificam a sessão original da proposta. |
| `ConfirmationDetails` | `data: date` obrigatório; opcionais `area: string`, `taxa: number >= 0` em reais, `nome: string`, `hora_inicio: string`, `hora_fim: string`. São os dados originais apresentados para revisão, não entrada substituta da decisão. |
| `ActionResult` | `status` enum reserved, cancelled, authorized, rejected, occupied, pending, policy_changed, policy_review_required, invalid_details, unknown_area, not_found, fee_changed; opcionais `code: string`, `id: integer`, `name: string`, `area: string`, `date: date`, `fee_cents: integer >= 0`. |
| `HistoryRead` | `messages: HistoryMessage[]`, `next_cursor: string ou null/ausente`, `confirmacoes_pendentes: PendingConfirmation[]`, `actions_enabled: boolean` (default false), `archived: boolean`. |
| `HistoryMessage` | `id: string` estável, `role: user ou assistant`, `content: string` público, `created_at: datetime`, `sourceSessionId: string`. |
| `ArchiveRead` | `archived: boolean`. Não representa exclusão ou reset de dados. |

O cursor `next_cursor` é opaco e volta em `before` para itens anteriores. A ordenação usa instante e identificador como desempate. Uma página pode estar vazia e ainda conter cursor quando a janela limitada de eventos ADK é interna; o cliente continua até cursor ausente. A consulta ORM limita as mensagens projetadas e a consulta ADK também possui janela limitada antes da materialização; não carrega o histórico inteiro para cortar somente a resposta. `include_archived=true` inclui mensagens anteriores ao corte sem restaurar ou remover registros. A autorização é revalidada para todas as sessões de origem agregadas. O histórico contém mensagens e recibos públicos; não contém pensamentos, instruções internas ou argumentos/resultados arbitrários de tools.

### Falhas e concorrência

Erros usam o [envelope do toolkit em F01](../F01-fundacao/spec.md#operação-e-erros-compartilhados). Sem bearer válido, 401; papel/vínculo insuficiente, 403; sessão ausente ou de outro titular, 404 SESSION_NOT_FOUND; entrada/cursor inválido, 422 INVALID_INPUT/INVALID_HISTORY_CURSOR. Uma decisão inexistente, alheia ou consumida retorna 409 sem novo efeito. Identidade indisponível falha fechada com 503.

A admissão é persistente e transacional, antes de criar o modelo/chamar Gemini: uma execução por sessão, uma por morador e quatro globais. Colisão de sessão retorna 409 CHAT_SESSION_CONFLICT; capacidade retorna 429 AGENT_CAPACITY_EXCEEDED; a janela de 60 s admite até dez turnos por morador e cem globais, com orçamento máximo de seis chamadas LLM por turno; excesso retorna 429 AGENT_RATE_LIMITED. Esses valores são constantes em AdmissionRepository, sem novas variáveis de ambiente. Não há retry automático ao provedor. Schema ausente retorna 503 AGENT_NOT_PREPARED; runtime desativado/credencial ausente, 503 AGENT_NOT_CONFIGURED; falha de provedor, 503 AGENT_UNAVAILABLE; cota Gemini, 503 AGENT_QUOTA_EXCEEDED. O 429 de admissão é distinto da indisponibilidade de cota externa.

`history_saved=false` informa que a resposta/efeito já ocorreu, mas o transcript não foi gravado. `pending_refresh_failed=true` preserva o recibo, mas exige atualizar pendências. Nenhum desses sinais autoriza repetir o efeito. Reenvio de decisão consumida permanece 409; o usuário deve consultar histórico e projeções. A sessão, a pendência original e os recibos persistem após reinício sem restore.

A UI retoma uma conversa contínua por titular/unidade, inclusive sessões autorizadas anteriormente arquivadas, sem lista de conversas ou botão de criar/arquivar. As rotas de arquivo são contrato de API; não adicionam esses controles à interface. O compositor permanece no rodapé; Enter envia e Shift+Enter quebra linha. O rascunho digitado durante resposta é preservado. F10 descreve a superfície acadêmica separada, sem JWT e com eventos completos.

## 6. Modelo de dados

Sessão da base registra identificador, dono, unidade e instante. Na integração, sessões, eventos e pendências precisam ser duráveis e independentes da memória do processo. Cada pendência conserva o vínculo com a sessão, o item original da ação e a decisão. Reenvio após decisão não repete efeito. A chave de proposta é gerada pelo servidor por turno e reutiliza a PK existente do ledger; o envelope transitório não é fonte de aprovação durável. A memória do runtime apenas evita repetir uma execução dentro do turno admitido, sem substituir a proteção transacional.

## 7. Estratégia de testes

Além dos critérios abaixo, testar com o Runner real e modelo controlado: correspondência entre o schema anunciado e a validação do servidor, projeção de campos de negócio conhecidos mas não utilizados, validação explícita de todos os tipos e rejeição de chaves desconhecidas ou de autoridade; destino calculado; ausência de ferramenta; transferência direta; filho incorreto; contexto de outro turno; execução duplicada/paralela; dados incompletos sem efeito; resposta canônica e recibo preservado diante de falha posterior. Em sessão existente com recusas anteriores, preservar os eventos e comprovar que visita válida produz pendência e que o pedido seguinte de reserva paga usa a mensagem atual. Repetir os fluxos relevantes com o provedor real e manter a prova de identidade, confirmação, privacidade e reinício.


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F09-AC01 | Integração do agente. Registrar identidade entregue à tool e comparar resposta, eventos e projeções diante do pedido de troca. | As tools continuam no escopo da unidade escolhida na abertura. |
| F09-AC02 | Base. Enviar POST de abertura com JWT administrativo e comparar as sessões existentes. | O serviço recusa a sessão e não faz ação em nome de outra conta. |
| F09-AC03 | Integração do agente. Criar pendência, reiniciar sem restaurar, aprovar e comparar agenda e reenvio. | Após reinício a decisão válida produz um efeito e o reenvio sequencial retorna 409. |
| F09-AC04 | Integração do agente. Comparar a versão do regulamento, resposta, tool chamada e texto persistido em eventos. | A resposta usa o horário vigente e os eventos não contêm assuntos não consultados. |
| F09-AC05 | Base. Abrir sessão, recarregar o navegador, consultar o detalhe e enviar texto com o agente desativado. | Após reabrir a tela a unidade continua fixa e a mensagem recebe indisponibilidade identificável. |
| F09-SEC01 | Base. Criar sessões de contas distintas e testar consulta e mensagem com o bearer de outra conta. | Uma sessão alheia não é legível nem utilizável e o vínculo vigente é checado nas ações privadas. |
| NFR01-AC01 | Base: HTTP real. Dado QA_SESSION_A é sessão de QA_A/9101 e QA_B tem outra unidade; quando solicitar GET /api/resident/chat/sessions/{QA_SESSION_A}/history com QA_B. | Então HTTP 404 SESSION_NOT_FOUND e nenhum texto ou pendência da sessão de QA_A. |
| NFR02-AC01 | Integração do agente: HTTP real e reinício. Dado QA_SESSION_A tem uma mensagem pública e uma confirmação QA_PENDING ainda pendente; quando reiniciar agent sem restore, ler /history e decidir QA_PENDING com QA_A; reenviar a decisão. | Então histórico e pendência sobrevivem, primeira decisão válida produz um efeito e segunda retorna 409 sem duplicação. |
| NFR03-AC01 | Integração do agente: HTTP real. Dado Duas sessões próprias possuem textos sintéticos distintos e o modelo recebeu instrução interna de roteamento; quando ler /history de QA_SESSION_A com QA_A após uma resposta e inspecionar o texto público. | Então retorna só mensagens e recibos autorizados; exclui texto de QA_B, instruções internas, payloads de tools, bearer e segredos. |
| F09-AC06 | Abrir o assistente com histórico, navegar para outra tela, retornar e recarregar em desktop e celular. | Mesma sessão retomada, histórico visível, uma linha do tempo e compositor no rodapé sem controles de múltiplas conversas. |
