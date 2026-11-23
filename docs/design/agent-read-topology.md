# Principal + especialistas com auditoria persistida

Estado: opt-in, validado com fake/SQLite. Não altera demo8793, Gemini ou rotas.

## Decisão corrigida após revisão
A primeira versão usava AgentTool. O código instalado do ADK2.9.1 mostra que
AgentTool cria Runner com InMemorySessionService e retorna apenas o texto final.
Assim, a chamada/resultados de list_my_reservations desapareciam da auditoria
persistida do principal. Isso não satisfaz F10, mesmo com resposta correta.

Substituímos por sub_agents e transferência nativa na MESMA sessão/invocação.
Não copiamos eventos manualmente nem usamos APIs privadas para reconstruir log.

```text
respond → gate identidade/sessão/vínculo
        → principal
        → transfer_to_agent(reservas)
        → reservas → list_my_reservations → query autorizada
        → reservas responde

próximo assunto → reservas → transfer_to_agent(principal)
                          → transfer_to_agent(convivencia)
                          → convivência responde limitação

Todos os eventos → mesmo DatabaseSessionService → persistência
```

## Trechos reais
`runtime/multi_agent_read.py`:
```python
sub_agents=[self.reservas, self.convivencia]
```
O ADK fornece transfer_to_agent. Não são ferramentas que abrem sessões filhas
voláteis. O especialista responde diretamente, sem exigir resumo final do principal.

```python
disallow_transfer_to_peers=True
```
Especialistas voltam ao principal para trocar de assunto, em vez de rotear entre
si. Prompts descrevem esse retorno. Reservas tem a única tool de domínio ligada;
convivência aceita opcionalmente a tool seletiva de regulamento; visitas ainda não estão conectadas.

```python
APP_NAME = "aurora_multi_read"
```
Namespace distinto preserva demo/histórico anterior. A autorização anterior ao
Runner e a rechecagem dentro da tool continuam herdadas da implementação de leitura.

## Provas
57 testes backend passaram. Cinco da topologia comprovam roteamento, troca de
assunto, revogação, configuração explícita e auditoria após fechar/reabrir banco.
O novo teste encontra no armazenamento:
- principal: chamada transfer_to_agent;
- reservas: chamada list_my_reservations;
- reservas: resposta da tool com reservations;
- IDs de evento únicos; outro user_id não recupera a sessão.
O teste usa Runner real e SQLite temporário, modelo fake sem rede. Não aumentamos
max_llm_calls para esconder loops: corrigimos o fake para distinguir o pedido do
usuário das transcrições citadas que o ADK fornece durante transferência.

## Limites
Conviver com dois especialistas estruturais não fecha os requisitos funcionais:
regulamento por trechos tem implementação opt-in (ver agent-regulation-excerpts.md); visitas ainda não estão conectadas. Prompt não prova
resistência de modelo real. Confirmação suspensa/retomada precisa teste próprio
nesta topologia; ledger/outbox não estão ligados. Ainda faltam PostgreSQL,
endpoints F10 e15 passos completos. A demo anterior permanece intacta.
