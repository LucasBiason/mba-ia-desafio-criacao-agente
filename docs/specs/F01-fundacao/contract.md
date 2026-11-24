# Contrato de verificação — F01 — Fundação executável

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F01-01** (P0D, cobre F01-AC01) — Um clone com Docker e o cliente Compose e os dados iniciais. Validar o manifesto, subir os jobs de preparação e a composição de teste, conferir todos os serviços contínuos saudáveis e abrir a origem publicada -> A composição inicia os componentes definidos, conclui os preparadores e publica o portal e a API do assistente. Modo: Base.
- **E2E-F01-02** (P0D, cobre F01-AC02) — Uma configuração obrigatória de autenticação ausente numa composição descartável. Em uma cópia temporária da configuração, omitir AURORA_JWT_KEY e executar docker compose config -q; conferir exit não zero e saída sanitizada -> O Compose recusa a configuração com AURORA_JWT_KEY ausente antes de iniciar os serviços e identifica somente o nome da variável. Modo: Base.
- **E2E-F01-03** (P0D, cobre F01-AC03) — Uma edição persistida em volume existente. Criar uma conta e alterar um cadastro, reiniciar os serviços e consultar os dois pelas mesmas APIs -> A edição continua após reiniciar e a carga inicial não a sobrescreve. Modo: Base.
- **E2E-F01-04** (P0D, cobre F01-SEC01) — Um cliente na origem publicada. Consultar a superfície pública de desenvolvimento e confirmar que a rota interna não está exposta -> O proxy expõe caminhos públicos e privados esperados e mantém as rotas internas fechadas. Modo: Base.
- **E2E-F01-05** (P0D, cobre NFR02-AC01) — Dado Uma conta QA_USER e a área QA_AREA criadas pelas APIs administrativas no volume descartável; quando reiniciar users e common-areas sem executar restore e consultar GET /api/admin/users/{QA_USER} e GET /api/admin/areas/{QA_AREA} -> Então ambos retornam 200 com os mesmos identificadores e valores gravados, sem duplicação. Modo: Base: HTTP real e reinício.
- **E2E-F01-06** (P0D, cobre NFR04-AC01) — Dado Uma composição isolada recém-preparada com configuração válida; quando executar make config e make up; conferir jobs identity-init, condo-init, session-init e agent-init concluídos, GET / e GET /docs nas respectivas portas -> Então manifesto válido, preparadores exit 0, portal 200 e documentação do assistente 200; liveness não certifica o provedor. Modo: Base: Compose e HTTP real.

- **E2E-F01-07** (P0D, cobre F01-AC04) — Configurar aplicações com a biblioteca e enviar chamadas válidas, sem identidade e com dados inválidos -> Correlação presente, erro sanitizado e logs sem credenciais ou payloads. Modo: testes HTTP da biblioteca e API real em QA.
- **E2E-F01-08** (P0D, cobre F01-AC05) — Executar importador com cadastros ausentes e repetir a execução -> Cadastros criados por API, repetição sem duplicações e JSONs originais intactos. Modo: API real em QA.

- **E2E-F01-09** (P0D, cobre F01-AC06) — Construir os oito serviços, executar o gate de camadas e consultar health, Swagger e OpenAPI -> Cada domínio tem camadas e modelos ORM próprios, health de liveness fornecido pelo toolkit sem consultar banco e contratos documentados. Modo: AST e HTTP em QA.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F01-01 | F01-AC01 | Base |
| E2E-F01-02 | F01-AC02 | Base |
| E2E-F01-03 | F01-AC03 | Base |
| E2E-F01-04 | F01-SEC01 | Base |
| E2E-F01-05 | NFR02-AC01 | Base |
| E2E-F01-06 | NFR04-AC01 | Base |

| E2E-F01-07 | F01-AC04 | Base |
| E2E-F01-08 | F01-AC05 | Base |

| E2E-F01-09 | F01-AC06 | Base |
