# Plano de implementação — F12 — Visão geral administrativa

## Dependências

F02, F05, F07. Reconciliação retrospectiva da entrega existente. Consulte a [spec](spec.md) e a [situação de entrega](../../entrega-01.md).

## Passos de implementação

### SI12.1 — Revisar o comportamento entregue

- Tipo: comportamento.
- Depende de: identidade e projeções existentes.
- Ações: conferir web/src/admin.jsx; services/domain/app.py contra cada cenário do PRD e preservar as rotas existentes.
- Testes: exercitar as jornadas dos critérios no desktop e celular, conferir chamadas e saída.
- Critérios: F12-AC01, F12-AC02, F12-SEC01.

### SI12.2 — Consolidar o aceite

- Tipo: comportamento.
- Depende de: SI12.1 e ambiente de revisão.
- Ações: registrar execução por cenário e submeter o pacote à revisão humana.
- Testes: conferir o resultado observado e os limites de cada evidência.
- Critérios: F12-AC01, F12-AC02, F12-SEC01.

### SI12.3 — Conferir segurança e privacidade

- Tipo: comportamento.
- Depende de: API autenticada existente.
- Ações: revisar a projeção usada pela tela e exercitar as recusas de acesso.
- Testes: enviar requisições negativas e inspecionar respostas sanitizadas.
- Critérios: NFR01-AC01, NFR03-AC01.
