---
spec_template: 1
feature: F09
ceremony: full
prd_source: docs/prd/functional/F09-chat-agente.md
---

# F09 — Chat do morador e agente

## 1. Visão técnica

A base permite abrir e retomar sessões pelo perfil morador. A tela informa a indisponibilidade do assistente quando o agente não está configurado. A aula implementará, em entregas pequenas, um principal que encaminha a especialistas, tools de domínio, consulta ao trecho adequado do regulamento e retomada de confirmações.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F09](../../prd/functional/F09-chat-agente.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../arquitetura.md). Este documento especifica os contratos da base e das etapas da aula identificadas na matriz.

## 2. Impacto arquitetural

O frontend envia mensagens à API autenticada. A API encaminhará à fronteira privada do serviço de agente somente depois de autorizar usuário e unidade. O contexto de identidade vem do servidor, e o especialista usa portas de domínio para consultar e registrar efeitos. A visão acadêmica usa um adaptador isolado para o contexto inicial fornecido pelo avaliador.

## 3. Decisões técnicas

Preservar a sessão com unidade escolhida na abertura; mudar a unidade inicia outra sessão. Para a aula, propor especialistas de reservas e convivência. Convivência usa ferramentas de visitas e de regulamento. A topologia de delegação e o modelo exato serão escolhidos na prática. Tratar entrada de conversa como intenção e aplicar regras no domínio.

As tools operam no contexto verificado da sessão. Cada apartamento tem até um responsável cadastrado como usuário `resident`. Para este escopo ele é também o proprietário. Outros ocupantes ficam fora do cadastro. A tool recebe do servidor a identidade do morador e a unidade selecionada e usa ambas para verificar vínculo e titularidade. Horários presentes nas projeções ajudam a responder consultas. A reserva continua exclusiva por área e dia.

## 4. Visão de componentes

- Chat React apresenta sessão, unidade selecionada, entrada e mensagem de indisponibilidade.
- API de condomínio autentica, abre sessão, verifica titularidade e encaminha ao limite do agente.
- Serviço privado do agente dá lugar ao futuro Runner, estrutura de especialistas e política de consulta.
- Adaptadores futuros mapeiam eventos, ferramentas autorizadas, pendências e confirmação para as APIs de produto e acadêmica.

## 5. Contratos de interface

POST `/api/resident/chat/sessions` recebe `apartment` e devolve 201 com `id`, `apartment`, `created_at` e status `awaiting_agent`. GET sobre a coleção ou `/{id}` lista ou consulta sessões do titular ainda vinculado. POST `/api/resident/chat/sessions/{id}/messages` recebe `message` de 1 a 2000 caracteres após remover espaços nas extremidades. A API encaminha ao destino privado `/internal/chat/messages` com identificação reconstruída no servidor. A fronteira devolve HTTP 503 com `AGENT_NOT_CONFIGURED` até a aula conectar o agente. Mensagens sem processamento ficam fora do histórico persistido. F10 detalha os contratos futuros de conversa, eventos e confirmação acadêmica. O produto não publica a interface interna do agente.

Unidade sem vínculo retorna recusa. Sessão inexistente ou alheia não expõe dados. Sem agente configurado, mensagem resulta em indisponibilidade observável e não indica sucesso. Na aula, falhas de modelo ou gravação não concedem efeitos.

## 6. Modelo de dados

Sessão da base registra identificador, dono, unidade e instante. Na aula, sessões, eventos e pendências precisam ser duráveis e independentes da memória do processo. Cada pendência conserva o vínculo com a sessão, o item original da ação e a decisão. Reenvio após decisão não repete efeito.

## 7. Estratégia de testes

O [contrato](contract.md) organiza as verificações por critério. Use credenciais locais e massa descartável. **Base** é o comportamento especificado para a aplicação preparada. **Aula do agente** e **Avaliação acadêmica** identificam os testes das etapas guiadas. O [registro de validação](../../validacao.md) indica quais verificações foram de fato executadas.

| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F09-AC01 | Aula do agente. Registrar identidade entregue à tool e comparar resposta, eventos e projeções diante do pedido de troca. | As tools continuam no escopo da unidade escolhida na abertura. |
| F09-AC02 | Base. Enviar POST de abertura com JWT administrativo e comparar as sessões existentes. | O serviço recusa a sessão e não faz ação em nome de outra conta. |
| F09-AC03 | Aula do agente. Criar pendência, reiniciar sem restaurar, aprovar e comparar agenda e reenvio. | Após reinício a decisão válida produz um efeito e o reenvio sequencial retorna 409. |
| F09-AC04 | Aula do agente. Comparar a versão do regulamento, resposta, tool chamada e texto persistido em eventos. | A resposta usa o horário vigente e os eventos não contêm assuntos não consultados. |
| F09-AC05 | Base. Abrir sessão, recarregar o navegador, consultar o detalhe e enviar texto com o agente desativado. | Após reabrir a tela a unidade continua fixa e a mensagem recebe indisponibilidade identificável. |
| F09-SEC01 | Base. Criar sessões de contas distintas e testar consulta e mensagem com o bearer de outra conta. | Uma sessão alheia não é legível nem utilizável e o vínculo vigente é checado nas ações privadas. |
| NFR01-AC01 | Base. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR02-AC01 | Base. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. | Efeito confirmado permanece. A falha é observável e o domínio fica consistente. |
| NFR03-AC01 | Base. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |

### Situação da execução

Parcial. Sessão persistida, seleção de unidade e indicação de indisponibilidade do agente. Fonte do código: `services/domain/app.py; services/agent/app.py; web/src/resident.jsx`. As evidências disponíveis são tests/test_api.py — sessão e histórico; ADK, tools, eventos e confirmação pendentes. Esta revisão é retrospectiva e não atesta a ordem histórica de invocação das skills. Critérios de aula e avaliação continuam pendentes. A [entrega](../../entrega-01.md) concentra o fechamento.

Revisão das fontes: índice atualizado com F11–F14 conferido; IDs e dependências de domínio anteriores preservados.

Conferência final: comportamentos do requisito vinculados aos procedimentos de aceite e situação da primeira entrega.
