# Plano de implementação — F12 — Visão geral administrativa

## Dependências


## Passos de implementação

### SI12.1 — Revisar o comportamento entregue

- Tipo: comportamento.
- Depende de: identidade e projeções existentes.
- Ações: conferir services/frontend/src/admin.jsx; services/apartments/main.py contra cada cenário do PRD e preservar as rotas existentes.
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
- Testes: solicitar GET /api/admin/apartments, /api/admin/areas e /api/admin/reservations com QA_A; confirmar que as três chamadas retornam 403 sem totais ou registros administrativos; comparar cards com GET /api/admin/apartments, /api/admin/areas e /api/admin/reservations e inspecionar os corpos; confirmar que contagens coincidem e nenhuma projeção contém senha, hash ou bearer.
- Critérios: NFR01-AC01, NFR03-AC01.
