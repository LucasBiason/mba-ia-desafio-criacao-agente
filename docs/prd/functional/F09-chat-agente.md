# F09 — Chat do morador e agente

Domínio: Agentes | Onda: 6 | Prioridade: 1

Requisitos não funcionais relacionados: NFR01, NFR02, NFR03

## Descrição

O portal autenticado integra Google ADK/Gemini, múltiplos especialistas por sessão e tools com escopo de unidade. As funções administrativas não exigem uma chamada ao modelo. O aceite exige verificar as jornadas e a persistência no corte candidato.

Oferecer uma conversa contínua por unidade, histórico recuperado automaticamente, consultas e ações de domínio com confirmação pela API. A interface ocupa a área de trabalho com uma linha do tempo e o campo de mensagem no rodapé; não apresenta lista de conversas nem ação para criar outra conversa na mesma unidade.

Como morador, quero abrir o chat em uma unidade vinculada. A integração com o domínio deve preservar o contexto da sessão.

A referência de produto original é FR09. A correspondência dos critérios anteriores é F09-AC01 ↔ FR09/AC01, F09-AC02 ↔ FR09/AC02, F09-AC03 ↔ FR09/AC03, F09-AC04 ↔ FR09/AC04. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Depende de: F06, F07, F08.
- Fornece: Sessão com usuário e unidade estáveis na base e fronteira de integração documentada para o agente principal e especialistas.
- Integração: O frontend envia mensagens à API autenticada. A API encaminha à fronteira privada do serviço de agente somente depois de autorizar usuário e unidade. O contexto de identidade vem do servidor, e o especialista usa portas de domínio para consultar e registrar efeitos. A interface do assistente usa um adaptador isolado para o contexto inicial fornecido pelo avaliador.

## Comportamento esperado

- **Dado** uma conta moradora tem duas unidades, abre sessão em uma e solicita mudança por mensagem
- **Quando** registrar identidade entregue à tool e comparar resposta, eventos e projeções diante do pedido de troca
- **Então** as tools continuam no escopo da unidade escolhida na abertura.

- **Dado** uma conta administrativa tenta abrir chat em nome de um morador
- **Quando** enviar POST de abertura com JWT administrativo e comparar as sessões existentes
- **Então** o serviço recusa a sessão e não faz ação em nome de outra conta.

- **Dado** uma reserva paga aguarda confirmação antes de reiniciar o processo
- **Quando** criar pendência, reiniciar sem restaurar, aprovar e comparar agenda e reenvio
- **Então** após reinício a decisão válida produz um efeito e o reenvio sequencial retorna 409.

- **Dado** o morador pergunta pelo horário de fechamento da piscina aos domingos
- **Quando** comparar a versão do regulamento, resposta, tool chamada e texto persistido em eventos
- **Então** a resposta usa o horário vigente e os eventos não contêm assuntos não consultados.

- **Dado** um morador abre uma sessão numa unidade autorizada e envia uma mensagem
- **Quando** abrir sessão, recarregar o navegador, consultar o detalhe e enviar texto com o agente desativado
- **Então** após reabrir a tela a unidade continua fixa e a mensagem recebe indisponibilidade identificável.

- **Dado** um morador já possui mensagens na unidade selecionada
- **Quando** abrir o assistente, navegar para outra tela e retornar, ou recarregar o navegador
- **Então** a mesma conversa é retomada com o histórico, sem selecionar ou criar outra conversa.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F09-AC01 | Uma conta moradora tem duas unidades, abre sessão em uma e solicita mudança por mensagem | As tools continuam no escopo da unidade escolhida na abertura | Registrar identidade entregue à tool e comparar resposta, eventos e projeções diante do pedido de troca |
| F09-AC02 | Uma conta administrativa tenta abrir chat em nome de um morador | O serviço recusa a sessão e não faz ação em nome de outra conta | Enviar POST de abertura com JWT administrativo e comparar as sessões existentes |
| F09-AC03 | Uma reserva paga aguarda confirmação antes de reiniciar o processo | Após reinício a decisão válida produz um efeito e o reenvio sequencial retorna 409 | Criar pendência, reiniciar sem restaurar, aprovar e comparar agenda e reenvio |
| F09-AC04 | O morador pergunta pelo horário de fechamento da piscina aos domingos | A resposta usa o horário vigente e os eventos não contêm assuntos não consultados | Comparar a versão do regulamento, resposta, tool chamada e texto persistido em eventos |
| F09-AC05 | Um morador abre uma sessão numa unidade autorizada e envia uma mensagem | Após reabrir a tela a unidade continua fixa e a mensagem recebe indisponibilidade identificável | Abrir sessão, recarregar o navegador, consultar o detalhe e enviar texto com o agente desativado |
| F09-AC06 | O morador possui histórico na unidade selecionada | Uma única conversa contínua restaura as mensagens automaticamente, sem lista de conversas ou botão de nova conversa | Abrir, sair e retornar ao assistente, recarregar em desktop e celular e conferir histórico e identificação da mesma sessão |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F09-chat-agente/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F09-SEC01 | Fronteiras e escopo | Uma sessão alheia não é legível nem utilizável e o vínculo vigente é checado nas ações privadas | Criar sessões de contas distintas e testar consulta e mensagem com o bearer de outra conta |

## Fora do escopo

Pagamento real, ações em nome de outra conta e uso de dados de unidades alheias como memória do modelo.

## Tratamento de erros

Unidade sem vínculo retorna recusa. Sessão inexistente ou alheia não expõe dados. Sem agente configurado, mensagem resulta em indisponibilidade observável e não indica sucesso. Na integração, falhas de modelo ou gravação não concedem efeitos.
