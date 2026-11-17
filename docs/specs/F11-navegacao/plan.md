# Plano de implementação — F11 — Navegação responsiva por perfil

## Dependências


## Passos de implementação

### SI11.1 — Revisar o comportamento entregue

- Tipo: comportamento.
- Depende de: identidade e projeções existentes.
- Ações: conferir web/src/app.jsx; web/src/ui.jsx; web/src/styles/app.css contra cada cenário do PRD e preservar as rotas existentes.
- Testes: exercitar as jornadas dos critérios no desktop e celular, conferir chamadas e saída.
- Critérios: F11-AC01, F11-AC02, F11-AC03, F11-AC04, F11-SEC01.

### SI11.2 — Consolidar o aceite

- Tipo: comportamento.
- Depende de: SI11.1 e ambiente de revisão.
- Ações: registrar execução por cenário e submeter o pacote à revisão humana.
- Testes: conferir o resultado observado e os limites de cada evidência.
- Critérios: F11-AC01, F11-AC02, F11-AC03, F11-AC04, F11-SEC01.

### SI11.3 — Conferir segurança e privacidade

- Tipo: comportamento.
- Depende de: API autenticada existente.
- Ações: revisar a projeção usada pela tela e exercitar as recusas de acesso.
- Testes: enviar requisições negativas e inspecionar respostas sanitizadas.
- Critérios: NFR01-AC01, NFR03-AC01.
