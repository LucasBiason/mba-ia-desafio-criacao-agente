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

### SI01.4 — Integrar a fundação HTTP e o importador por API

- Tipo: comportamento.
- Depende de: composição e cadastros administrativos existentes.
- Ações: instalar microservice-toolkit por dependência local empacotada, configurar os verificadores de identidade e implementar o importador administrativo por API.
- Testes: executar testes unitários HTTP da biblioteca, nove casos integrados do domínio, importação e repetição em QA e prova de runtime.
- Critérios: F01-AC04, F01-AC05.

### SI01.5 — Separar serviços e impor as camadas FastAPI

- Tipo: comportamento.
- Depende de: SI01.4 e contratos de cadastros existentes.
- Ações: separar os domínios em processos, adotar repositories SQLAlchemy, validators e serializers e centralizar health e documentação no toolkit.
- Testes: executar o gate de camadas, conferir Swagger e OpenAPI dos serviços, repetir os contratos HTTP e comparar os dados após preparar e reiniciar.
- Critérios: F01-AC06, F01-AC03, F01-AC04.


### SI01.6 — Consolidar o framework e separar a preparação dos dados

- Tipo: infraestrutura.
- Depende de: SI01.5 e ADR-0007.
- Ações: organizar o toolkit nos módulos da referência Shared; mover identidade, permissões e tipos Aurora ao aurora-toolkit; deixar somente domínios em services; renomear settings para parameters; usar REQUIRED_SECRETS no lifespan do framework e bootstrap explícito por componente, sem upgrade legado.
- Testes: executar a suíte do toolkit, os contratos HTTP/OpenAPI e a preparação repetida em volumes descartáveis; interromper apenas o banco do piloto, confirmar health 200 e operação de negócio 503, restaurar e comparar estado; verificar admin autorizado, morador 403 e chamada anônima 401 em apartments.
- Critérios: F01-AC02, F01-AC03, F01-AC04, F01-AC06, F01-SEC01.
