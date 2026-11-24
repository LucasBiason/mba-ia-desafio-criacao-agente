# Contrato de verificação — F09 — Chat do morador e agente

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F09-01** (P0D, cobre F09-AC01) — Uma conta moradora tem duas unidades, abre sessão em uma e solicita mudança por mensagem. Registrar identidade entregue à tool e comparar resposta, eventos e projeções diante do pedido de troca -> As tools continuam no escopo da unidade escolhida na abertura. Modo: Integração do agente.
- **E2E-F09-02** (P0D, cobre F09-AC02) — Uma conta administrativa tenta abrir chat em nome de um morador. Enviar POST de abertura com JWT administrativo e comparar as sessões existentes -> O serviço recusa a sessão e não faz ação em nome de outra conta. Modo: Base.
- **E2E-F09-03** (P0D, cobre F09-AC03) — Uma reserva paga aguarda confirmação antes de reiniciar o processo. Criar pendência por delegação tipada na mesma conversa usada para uma visita, conferir detalhes da mensagem atual e zero reserva antecipada, reiniciar sem restaurar, aprovar e comparar agenda e reenvio -> Após reinício a decisão válida produz um efeito e o reenvio sequencial retorna 409. Modo: Integração do agente.
- **E2E-F09-04** (P0D, cobre F09-AC04) — O morador pergunta pelo horário de fechamento da piscina aos domingos. Comparar a versão do regulamento, resposta, tool chamada e texto persistido em eventos -> A resposta usa o horário vigente e os eventos não contêm assuntos não consultados. Modo: Integração do agente.
- **E2E-F09-05** (P0D, cobre F09-AC05) — Um morador abre uma sessão numa unidade autorizada e envia uma mensagem. Abrir sessão, recarregar o navegador, consultar o detalhe e enviar texto com o agente desativado -> Após reabrir a tela a unidade continua fixa e a mensagem recebe indisponibilidade identificável. Modo: Base.
- **E2E-F09-06** (P0D, cobre F09-SEC01) — Dois moradores têm sessões distintas ou uma conta perde o vínculo anterior. Criar sessões de contas distintas e testar consulta e mensagem com o bearer de outra conta -> Uma sessão alheia não é legível nem utilizável e o vínculo vigente é checado nas ações privadas. Modo: Base.
- **E2E-F09-07** (P0D, cobre NFR01-AC01) — Dado QA_SESSION_A é sessão de QA_A/9101 e QA_B tem outra unidade; quando solicitar GET /api/resident/chat/sessions/{QA_SESSION_A}/history com QA_B -> Então HTTP 404 SESSION_NOT_FOUND e nenhum texto ou pendência da sessão de QA_A. Modo: Base: HTTP real.
- **E2E-F09-08** (P0D, cobre NFR02-AC01) — Dado QA_SESSION_A tem uma mensagem pública e uma confirmação QA_PENDING ainda pendente; quando reiniciar agent sem restore, ler /history e decidir QA_PENDING com QA_A; reenviar a decisão -> Então histórico e pendência sobrevivem, primeira decisão válida produz um efeito e segunda retorna 409 sem duplicação. Modo: Integração do agente: HTTP real e reinício.
- **E2E-F09-09** (P0D, cobre NFR03-AC01) — Dado Duas sessões próprias possuem textos sintéticos distintos e o modelo recebeu instrução interna de roteamento; quando ler /history de QA_SESSION_A com QA_A após uma resposta e inspecionar o texto público -> Então retorna só mensagens e recibos autorizados; exclui texto de QA_B, instruções internas, envelope/JSON de delegação, payloads arbitrários de tools, bearer e segredos. Somente o recibo emitido pelo servidor pode informar efeito confirmado. Modo: Integração do agente: HTTP real.

- **E2E-F09-10** (P0D, cobre F09-AC06) — Um morador com mensagens na unidade selecionada. Abrir o assistente, navegar para outra tela, retornar e recarregar em desktop e celular -> A mesma conversa e o histórico são retomados automaticamente, sem lista ou criação de conversas e com campo de mensagem no rodapé. Modo: Portal.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F09-01 | F09-AC01 | Integração do agente |
| E2E-F09-02 | F09-AC02 | Base |
| E2E-F09-03 | F09-AC03 | Integração do agente |
| E2E-F09-04 | F09-AC04 | Integração do agente |
| E2E-F09-05 | F09-AC05 | Base |
| E2E-F09-06 | F09-SEC01 | Base |
| E2E-F09-07 | NFR01-AC01 | Base |
| E2E-F09-08 | NFR02-AC01 | Integração do agente |
| E2E-F09-09 | NFR03-AC01 | Integração do agente |
| E2E-F09-10 | F09-AC06 | Portal |
