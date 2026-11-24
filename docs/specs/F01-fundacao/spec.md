---
spec_template: 1
feature: F01
ceremony: full
prd_source: docs/prd/functional/F01-fundacao.md
---

# F01 — Fundação executável

## 1. Visão técnica

Docker Compose parte de imagens versionadas e levanta o frontend React/Vite, o proxy Nginx, oito aplicações FastAPI por domínio, incluindo a fronteira do agente e as instâncias PostgreSQL de identidade e domínio. O cluster inclui a entrada do assistente e funciona com as fixtures do projeto e configuração local válida.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F01](../../prd/functional/F01-fundacao.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

O navegador chama o proxy em uma única origem. O proxy encaminha autenticação, usuários, apartamentos, áreas, agenda, visitas, configurações e chat para suas aplicações na rede do Compose. As bases e a fronteira interna do agente ficam na rede privada. A API do assistente tem entrada local própria na mesma composição, isolada do proxy e dos dados do portal.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0001](../../adr/ADR-0001-servicos-por-dominio-e-camadas.md), [ADR-0002](../../adr/ADR-0002-orm-e-integridade-transacional.md), [ADR-0004](../../adr/ADR-0004-toolkit-e-operacao-dos-servicos.md), [ADR-0006](../../adr/ADR-0006-persistencia-compartilhada-da-base.md) e [ADR-0007](../../adr/ADR-0007-framework-e-ciclo-de-vida.md) e [ADR-0008](../../adr/ADR-0008-cluster-unico-e-containers-por-servico.md).

Usar os bancos de identidade e condomínio para o portal, SQLite dedicado às sessões/eventos ADK do portal e PostgreSQL isolado para a API do desafio, conforme ADR-0006. Os serviços consomem identidade validada e mantêm repositories por domínio. As funções administrativas independem de chamadas ao modelo; o cluster completo requer a configuração de Gemini. A montagem das fixtures é somente leitura e a carga inicial é idempotente.

O toolkit cria o lifespan e valida REQUIRED_SECRETS. Os main.py não abrem banco, não criam tabelas nem carregam fixtures. identity-init, condo-init e os preparadores de sessões ADK executam antes dos servidores do portal; agent-init prepara a API do desafio. O bootstrap do agente cria histórico, ledger e admissão. Repetir a preparação preserva tabelas existentes; a partida HTTP não executa DDL.

## 4. Visão de componentes

- `web`: empacota React/Vite e Nginx e publica a porta local da interface.
- `auth` e `users`: expõem login, introspecção e gestão de contas sobre `identity-db`.
- `apartments`, `common-areas`, `agenda`, `visits` e `parameters`: mantêm seus recursos sobre `condo-db`, com camadas e autorização por domínio.
- `agent`: compõe principal, especialistas e ferramentas do portal.
- Réplicas do assistente e gateway: publicam o contrato de F10 com PostgreSQL separado.

## 5. Contratos de interface

A operação é exposta pelo Makefile e pelo único manifesto configs/compose.yaml. Cada serviço mantém seu Dockerfile e entrypoint; a raiz contém somente metadados Python de distribuição e os comandos agregadores, sem servidor ou imagem própria. A preparação em infra/setup_local.py preserva configs/.env existente, e make down preserva volumes. Configs contém somente Compose, configuração privada e exemplo. A organização segue o ADR-0008.

Execute `make up` para gerar a configuração local, construir e iniciar os serviços. Use `docker compose --env-file configs/.env -f configs/compose.yaml config -q` para conferir o manifesto com essa configuração e abra `http://127.0.0.1:8770/`. `GET /api/health` passa pelo proxy até o health do toolkit na aplicação de apartamentos. A prontidão de cada dependência é inspecionável por `docker compose ps`. A porta do assistente 8000 publica somente o gateway local do avaliador.

Configuração obrigatória ausente impede a partida do servidor. Banco inacessível impede a preparação inicial e retorna erro de dependência nas operações de negócio. O endpoint /health continua sendo liveness e não consulta o banco. O diagnóstico indica a falha sem imprimir credenciais. Uma indisponibilidade da fronteira do agente afeta a mensagem de chat e deixa os cadastros disponíveis.

### Operação e erros compartilhados

O [README](../../../README.md#modos-prontidão-e-recuperação) inventaria responsabilidade, dados, modos, prontidão funcional e recuperação por serviço. As configurações e defaults estão em [variáveis](../../../README.md#variáveis-e-defaults); logins públicos não incluem senha.

As APIs do toolkit retornam `{detail: ErrorDetail}` ou `detail` textual quando declarado pela fronteira. `ErrorDetail` contém `code` e `message`, com `fields?: [{field, code, message}]` na validação e `request_id?`, `method?`, `route?` em falhas correlacionadas. `debug?: {exception_type, message, traceback}` somente existe sob política de desenvolvimento/teste e é sanitizado; produção não expõe traceback. 401 indica sessão recusada, 403 falta de permissão, 404 recurso ausente, 409 conflito de estado, 422 entrada, 429 limite/cota, 500 falha interna e 503 dependência indisponível. O código e as condições específicas pertencem à seção 5 de cada domínio. Swagger declara schemas dos corpos e as credenciais efetivamente exigidas; não basta enumerar status.

`/health` é liveness; a prontidão funcional exige jobs concluídos e uma operação autorizada no domínio. O adapter de sessão ADK usa somente schema já preparado: a inspeção é de leitura e schema ausente produz indisponibilidade segura, sem DDL durante HTTP. A preparação explícita de sessões pertence ao job session-init no portal e ao comando init na API acadêmica.

## 6. Modelo de dados

Volumes distintos retêm contas, sessões de login, cadastros, revisões, reservas e autorizações. A carga lê os cinco arquivos originais e mantém um único estado inicial importado. A partida normal preserva alterações operacionais em vez de restaurar a base.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F01-AC01 | Base. Validar o manifesto, subir os jobs de preparação e a composição de teste, conferir todos os serviços contínuos saudáveis e abrir a origem publicada. | A composição inicia os componentes definidos, conclui os preparadores e publica o portal e a API do assistente. |
| F01-AC02 | Base. Em uma cópia temporária da configuração, omitir AURORA_JWT_KEY e executar docker compose config -q; conferir exit não zero e saída sanitizada. | O Compose recusa a configuração com AURORA_JWT_KEY ausente antes de iniciar os serviços e identifica somente o nome da variável. |
| F01-AC03 | Base. Criar uma conta e alterar um cadastro, reiniciar os serviços e consultar os dois pelas mesmas APIs. | A edição continua após reiniciar e a carga inicial não a sobrescreve. |
| F01-AC04 | Executar testes da biblioteca e chamar API com identidade válida, inválida e erro de validação | Erros seguros, autenticação aplicada e correlação propagada sem dados sensíveis nos logs |
| F01-AC05 | Importar uma vez, repetir e comparar cadastros e dados de origem em QA | Registros existentes conservados e novos cadastros criados apenas uma vez pelas APIs |
| F01-AC06 | Gate AST por serviço e chamadas de health, Swagger e OpenAPI via gateway | Camadas respeitadas, documentação acessível e liveness independente de banco por serviço |
| F01-SEC01 | Base. Consultar a superfície pública de desenvolvimento e confirmar que a rota interna não está exposta. | O proxy expõe caminhos públicos e privados esperados e mantém as rotas internas fechadas. |
| NFR02-AC01 | Base: HTTP real e reinício. Dado Uma conta QA_USER e a área QA_AREA criadas pelas APIs administrativas no volume descartável; quando reiniciar users e common-areas sem executar restore e consultar GET /api/admin/users/{QA_USER} e GET /api/admin/areas/{QA_AREA}. | Então ambos retornam 200 com os mesmos identificadores e valores gravados, sem duplicação. |
| NFR04-AC01 | Base: Compose e HTTP real. Dado Uma composição isolada recém-preparada com configuração válida; quando executar make config e make up; conferir jobs identity-init, condo-init, session-init e agent-init concluídos, GET / e GET /docs nas respectivas portas. | Então manifesto válido, preparadores exit 0, portal 200 e documentação do assistente 200; liveness não certifica o provedor. |

### Dependência de infraestrutura HTTP

O build instala microservice-toolkit por caminho relativo em infra/packages/microservice-toolkit. A cópia da biblioteca no contexto Docker antecede uv sync a partir da raiz do projeto. Criar as aplicações pelo factory configura logs, correlação e erros sem alterar os contratos de negócio. Os serviços de negócio configuram o verificador de identidade do aurora-toolkit para suas rotas privadas.

O teste de runtime continua exigindo composição isolada de avaliação em rede privada na porta publicada pelo ambiente e aceita COMPOSE_PROJECT_NAME para selecionar o ambiente descartável. Os testes de integração ficam dentro de services/apartments/tests/integration.
