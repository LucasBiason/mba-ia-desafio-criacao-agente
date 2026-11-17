# Plano de implementação — F14 — Consulta do próprio perfil

## Dependências


## Passos de implementação

### SI14.1 — Revisar o comportamento entregue

- Tipo: comportamento.
- Depende de: identidade e projeções existentes.
- Ações: conferir web/src/app.jsx; services/identity/app.py contra cada cenário do PRD e preservar as rotas existentes.
- Testes: exercitar as jornadas dos critérios no desktop e celular, conferir chamadas e saída.
- Critérios: F14-AC01, F14-AC02, F14-SEC01.

### SI14.2 — Consolidar o aceite

- Tipo: comportamento.
- Depende de: SI14.1 e ambiente de revisão.
- Ações: registrar execução por cenário e submeter o pacote à revisão humana.
- Testes: conferir o resultado observado e os limites de cada evidência.
- Critérios: F14-AC01, F14-AC02, F14-SEC01.

### SI14.3 — Conferir segurança e privacidade

- Tipo: comportamento.
- Depende de: API autenticada existente.
- Ações: revisar a projeção usada pela tela e exercitar as recusas de acesso.
- Testes: enviar requisições negativas e inspecionar respostas sanitizadas.
- Critérios: NFR01-AC01, NFR03-AC01.
