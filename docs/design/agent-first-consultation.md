# Primeiro resultado de consulta visível (F09)

## O avanço concreto
Antes, o frontend aguardava o POST mas descartava seu resultado e tentava ler
session.messages, campo que o contrato atual de sessão não fornece. Uma consulta
bem-sucedida ficaria invisível. Agora o chat mostra pergunta e resposta retornada
em `message`, separadas por session_id. Não houve novo contrato HTTP, entrypoint
acadêmico ou ativação do modelo real.

```text
Tela envia pergunta
 → API pública autoriza sessão
 → fronteira interna reautoriza contexto
 → Runner fake solicita list_my_reservations()
 → query SQL real filtra sessão + vínculo + titular original + status
 → projeção segura retorna ao Runner
 → texto final volta em message
 → tela mostra a resposta na conversa correta
```

## Trechos para Lucas estudar
Em `web/src/resident.jsx`, `const response = await api(...)` captura a resposta.
`setTurns(... [selectedId] ...)` vincula os turnos à conversa, e JSX mostra texto
normal, nunca HTML. Falhas401/403/404 limpam os turnos locais e reconsultam sessão.
QueryResult não renderiza conversa quando a consulta da sessão está recusada.
A tela informa que estes turnos não são restaurados ao recarregar. Histórico ADK
existe no backend experimental; expô-lo exige outra integração autorizada.

Em `test_adk_message_api.py`, o novo cenário substitui dublês de repository pelos
repositories reais sobre SQLite em arquivo. A massa contém reserva própria,
cancelada, de outra unidade do mesmo dono e de outro morador. A tool devolve
somente `mine`, sem resident_id. Após troca real do vínculo no SQL, a API pública
recusa404 e não acrescenta eventos ao histórico. O modelo e identidade externa
continuam fake; não afirmar que houve consulta Gemini real ou auth JWT real.

## Evidência
- 52 testes backend passaram, incluindo percurso HTTP→Runner→SQL real.
- Build Vite de produção passou em cópia temporária, sem modificar node_modules
  do checkout.
- Playwright Chromium headless viewport390 testou uma cópia do componente real
  com API fake: resposta visível, texto com tag script escapado, troca de conversa
  sem mistura e revogação ocultando resposta. Servidor temporário foi encerrado.
- Sem Docker/deploy novo, sem segredo, sem chamada paga, sem escrita de domínio.

## Limites de entrega
Isto é a primeira consulta de leitura utilizável quando uma composição é
explicitamente configurada. O produto continua503 por padrão. Não estão prontos:
principal+dois especialistas, regulamento por trechos, histórico na UI,
confirmações reais, adapter F10/15 passos e provedor real autorizado. A próxima
fatia deve escolher um desses requisitos de entrega, não ampliar infraestrutura.
