# Plano de implementação — F01 — Fundação executável

## Dependências


## Passos de implementação

### SI01.1 — Preparar volumes e inicialização

- Tipo: infraestrutura.
- Depende de: Início da base.
- Ações: Definir serviços, variáveis de partida, health checks e carga idempotente dos bancos.
- Testes: Executar docker compose config e iniciar composition de teste; verificar saúde explícita de cada dependência.
- Critérios: F01-AC01, F01-AC02.

### SI01.2 — Publicar a interface local e provar persistência

- Tipo: comportamento.
- Depende de: SI01.1.
- Ações: Servir o build pelo proxy de mesma origem, manter a rede interna e validar reinício sobre volumes existentes.
- Testes: Abrir o login, consultar /api/health, comparar alterações antes e depois de reinício e recusar rota de introspecção pública.
- Critérios: F01-AC03, F01-SEC01.

### SI01.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para fundação executável.
- Testes: Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. Executar o procedimento aplicável a partir de uma instalação isolada e registrar componentes, saídas e condições não exercitadas.
- Critérios: NFR02-AC01, NFR04-AC01.
