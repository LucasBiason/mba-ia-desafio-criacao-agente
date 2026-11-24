---
spec_template: 1
feature: F10
ceremony: full
prd_source: docs/prd/functional/F10-avaliacao.md
---

# F10 — Compatibilidade e aceite do desafio

## 1. Visão técnica

A avaliação inicia na porta local 8000, usando Python 3.12 ou superior, uv com manifesto e lock versionados na raiz, uma versão exata da série 2 de Google ADK e credencial do provedor somente no ambiente. O modo usa os arquivos iniciais intactos. É separado do proxy autenticado do produto. A entrada executável é python -m services.agent.api; o cluster inclui duas réplicas e gateway do assistente, enquanto o proxy do portal não publica essas rotas.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F10](../../prd/functional/F10-avaliacao.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

Um entrypoint dedicado traduz o protocolo do desafio para a mesma lógica de sessão, reconhecimento de intenções e regras de domínio. A interface integra o cluster com rede e armazenamento isolados do portal. O adaptador consulta projeções por apartamento definidas no protocolo; o proxy autenticado não roteia esses caminhos.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0004](../../adr/ADR-0004-toolkit-e-operacao-dos-servicos.md).

Reservar o contrato atual de produto com namespace /api e autenticação obrigatória. Usar um executável próprio para o avaliador, com PostgreSQL do assistente isolado e duas réplicas atrás do gateway. A versão Google ADK 2.14.1 está fixada no manifesto e lock. Executar restauração de dados como ação explícita do roteiro, fora da partida normal.

## 4. Visão de componentes

- Entrypoint local de avaliação, separado do frontend e do proxy de produto.
- Adaptador de sessões, mensagens, eventos, decisões e projeções no formato do enunciado.
- Roteiro de confirmação, persistência e concorrência para registro das provas.
- Fixtures do desafio com auditoria de integridade do conteúdo.

## 5. Contratos de interface

Superfície local sem autenticação, vinculada a loopback e isolada do portal (F10-AC01/F10-SEC01). As seis rotas de domínio abaixo preservam o protocolo do enunciado. `/docs`, `/openapi.json` e `/health` são endpoints operacionais adicionais. `session_id` é o identificador opaco retornado pela abertura; datas são strings AAAA-MM-DD. Entradas Pydantic usam tipos estritos e rejeitam chaves extras.

| Método e rota | Entrada e finalidade | Sucesso | Erros previstos |
| --- | --- | --- | --- |
| POST `/sessoes` | JSON `{apartamento: string}` com 1–32 caracteres; fixa a unidade fornecida pelo avaliador | 201 `{session_id: string}` | 422 entrada; 503 armazenamento não preparado/indisponível |
| POST `/sessoes/{session_id}/mensagens` | JSON `{texto: string}` com 1–4000 caracteres; executa turno na unidade persistida | 200 `MessageResponse` | 404 sessão; 409 turno/pendência/estado divergente; 422 entrada; 429 cota; 503 execução/armazenamento |
| POST `/sessoes/{session_id}/confirmacoes` | JSON `{id: string, confirmado: boolean}`; id 1–256 caracteres identifica pendência original; não aceita dados substitutos da ação | 200 `MessageResponse` | 404 sessão; 409 pendência alheia/inválida/consumida ou turno concorrente; 422 entrada; 429 cota; 503 execução/armazenamento |
| GET `/sessoes/{session_id}/eventos` | Path session_id; lê a sequência persistida de eventos ADK | 200 `EventsResponse`, array de objetos JSON completos em ordem | 404 sessão; 503 armazenamento |
| GET `/apartamentos/{numero}/reservas` | Path numero; projeção direta para verificação do avaliador | 200 array `ReservationRead` | 503 armazenamento |
| GET `/apartamentos/{numero}/visitantes` | Path numero; projeção direta para verificação do avaliador | 200 array `VisitorRead` | 503 armazenamento |

`MessageResponse` contém `resposta: string` (texto vazio permitido) e `confirmacoes_pendentes: PendingConfirmation[]`. Cada pendência tem `id: string`, `acao: string` e `detalhes: object` com valores JSON. Detalhes pertencem ao item proposto pelo servidor: a decisão só aceita id e booleano e não pode alterar área, data, nome ou unidade. `ReservationRead` possui `codigo`, `area` e `data`, todos strings; `VisitorRead` possui `nome` e `data`. Nenhuma projeção expõe IDs internos de proprietário. `EventsResponse` conserva objetos JSON ADK completos; não equivale ao histórico público filtrado do portal.

Erros de domínio e disponibilidade usam `{detail: string}` conforme `ErrorResponse`. Entrada inválida retorna 422 no envelope de validação publicado no OpenAPI, sem repetir credenciais. 429 informa cota do provedor, sem confundir a recusa com sucesso; 503 é indisponibilidade. O cliente deve ler eventos e projeções antes de repetir uma ação. Não há retry automático de efeitos.

O controller resolve o apartamento pelo vínculo persistido da sessão. A reserva gratuita não exige confirmação; cobrança e autorização de visita exigem a decisão externa. Decisão sequencial inexistente, consumida ou de outra sessão retorna 409 sem novo efeito. Transação, recibo idempotente e índice único parcial impedem repetição e reserva concorrente da mesma área/data. A preparação ORM e ADK é explícita em `init`; `serve` não cria tabelas. Restauração é comando separado e invalida sessões anteriores. A execução do protocolo e o aceite humano dependem de avaliação real do candidato.

## 6. Modelo de dados

A restauração do assistente exige decisão explícita do operador, repõe reservas e visitantes das fixtures em transação e invalida sessões/pendências anteriores. O comando é make restore; o executável exige restore --confirm-restore. Não afeta os bancos do portal. A partida normal retém eventos e efeitos. O ambiente do assistente deve usar isolamento lógico ou físico da persistência de produto.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F10-AC01 | Avaliação do desafio. Seguir o roteiro de partida, restaurar os dados, registrar códigos e observar estado e eventos em cada passo. | O avaliador executa os 15 passos na porta 8000 com o protocolo completo. |
| F10-AC02 | Base. Consultar rotas locais planejadas na origem do produto e tentar APIs privadas sem bearer. | Caminhos do assistente e rotas internas não contornam a autenticação. |
| F10-AC03 | Avaliação do desafio. Comparar hashes dos dados, revisar o lock e verificar os links das garantias. | Cinco fixtures correspondem à origem e o README identifica provas e trechos implementados. |
| F10-AC04 | Base. Conferir os hashes das fixtures antes da partida e depois do teste com volumes isolados. | As cinco fixtures mantêm o mesmo conteúdo entre a cópia e o ambiente inicializado. |
| F10-SEC01 | Avaliação do desafio. Conferir bind, isolamento de armazenamento, rota de autenticação do produto e diff de configuração. | O exercício roda localmente, com dados separados e sem publicar segredos. |
| NFR01-AC01 | Avaliação do desafio: Gemini e HTTP reais. Dado Uma sessão acadêmica fixa apartamento 101 e possui reserva paga pendente QA_PENDING; quando enviar texto sim em /sessoes/{QA_SESSION}/mensagens sem chamar /confirmacoes e consultar /apartamentos/101/reservas. | Então a ação permanece pendente e nenhuma reserva paga nova existe; somente decisão externa válida poderá liberá-la. |
| NFR03-AC01 | Avaliação do desafio: Gemini e HTTP reais. Dado QA_SESSION fixa apartamento 101 e outra sessão usa 202; quando pedir nomes de visitantes de 202 pela sessão 101 e inspecionar resposta, eventos e projeção de 101. | Então tools mantêm apartamento 101 e a resposta não revela nome de 202 ou segredos; eventos de execução não contêm credenciais. |
| NFR04-AC01 | Avaliação do desafio: PostgreSQL, Gemini e HTTP reais. Dado Uma composição isolada tem agent-a e agent-b sobre o mesmo agent-db; quando criar QA_SESSION via POST /sessoes, enviar consulta e ler eventos via gateway; reiniciar uma réplica sem restore e reler eventos. | Então as seis rotas estão disponíveis em 8000 e a mesma sessão/eventos persistem entre réplicas, sem estado do portal. |
