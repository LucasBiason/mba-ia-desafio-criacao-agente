---
spec_template: 1
feature: F01
ceremony: full
prd_source: docs/prd/functional/F01-fundacao.md
---

# F01 — Fundação executável

## 1. Visão técnica

Docker Compose parte de imagens versionadas e levanta o frontend React/Vite, o proxy Nginx, os serviços FastAPI de autenticação, usuários e condomínio, o limite de integração do agente e as instâncias PostgreSQL de identidade e domínio. A base funciona com as fixtures do projeto e uma configuração de desenvolvimento local.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F01](../../prd/functional/F01-fundacao.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.

## 2. Impacto arquitetural

O navegador chama o proxy em uma única origem. O proxy direciona autenticação, usuários e condomínio para serviços na rede do Compose. As bases e a fronteira interna do agente ficam na rede privada. A porta de avaliação acadêmica tem sua própria entrada futura, sem compartilhar o proxy de produto.

## 3. Decisões técnicas

Usar dois bancos de fronteira, identidade e condomínio, para que o serviço de domínio consuma a identidade validada e não manipule a tabela de contas. A base inicia sem credencial de modelo. A montagem das fixtures é somente leitura e a carga inicial é idempotente.

## 4. Visão de componentes

- `web`: empacota React/Vite e Nginx e publica a porta local da interface.
- `auth` e `users`: expõem login, introspecção e gestão de contas sobre `identity-db`.
- `condo`: mantém as projeções do condomínio em `condo-db`.
- `agent`: fornece o ponto de integração para a prática, com prontidão operacional própria.

## 5. Contratos de interface

A operação é exposta pelo Makefile, com `ENV=local|dev`. O Dockerfile usa estágios `development` e `production`; o entrypoint despacha `dev|runserver|prod|test` com `exec`. O modo dev usa `configs/compose.dev.yaml` com recarga automática. A preparação preserva `.env` existente, e `make down` preserva volumes. Não criar pasta `scripts` na raiz.

Execute `make up` para gerar a configuração local, construir e iniciar os serviços. Use `docker compose config -q` para conferir o manifesto com essa configuração e abra `http://127.0.0.1:8767/`. `GET /api/health` passa pelo proxy até a API de condomínio. A prontidão de cada dependência é inspecionável por `docker compose ps`. A porta acadêmica 8000 fica fora da composição base.

Configuração obrigatória ausente ou banco inacessível impedem prontidão da dependência. O diagnóstico indica a falha sem imprimir credenciais. Uma indisponibilidade da fronteira do agente afeta a mensagem de chat e deixa os cadastros disponíveis.

## 6. Modelo de dados

Volumes distintos retêm contas, sessões de login, cadastros, revisões, reservas e autorizações. A carga lê os cinco arquivos originais e mantém um único estado inicial importado. A partida normal preserva alterações operacionais em vez de restaurar a base.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F01-AC01 | Base. Validar o manifesto, subir a composição de teste, conferir serviços saudáveis e abrir a origem publicada. | A composição inicia as onze unidades e carrega a tela de login. |
| F01-AC02 | Base. Omitir a configuração em sandbox e comparar status do serviço e saída sanitizada. | O Compose recusa a configuração ou a autenticação fica sem prontidão. A falha identifica a variável sem divulgar segredo. |
| F01-AC03 | Base. Criar uma conta e alterar um cadastro, reiniciar os serviços e consultar os dois pelas mesmas APIs. | A edição continua após reiniciar e a carga inicial não a sobrescreve. |
| F01-AC04 | Executar testes da biblioteca e chamar API com identidade válida, inválida e erro de validação | Erros seguros, autenticação aplicada e correlação propagada sem dados sensíveis nos logs |
| F01-AC05 | Importar uma vez, repetir e comparar cadastros e dados de origem em QA | Registros existentes conservados e novos cadastros criados apenas uma vez pelas APIs |
| F01-AC06 | Gate AST por serviço e chamadas de health, Swagger e OpenAPI via gateway | Camadas respeitadas, documentação acessível e prontidão da dependência por serviço |
| F01-SEC01 | Base. Consultar a superfície pública de desenvolvimento e confirmar que a rota interna não está exposta. | O proxy expõe caminhos públicos e privados esperados e mantém as rotas internas fechadas. |
| NFR02-AC01 | Base. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. | Efeito confirmado permanece. A falha é observável e o domínio fica consistente. |
| NFR04-AC01 | Base. Executar o procedimento aplicável a partir de uma instalação isolada e registrar componentes, saídas e condições não exercitadas. | As dependências do modo escolhido atingem prontidão e os verificadores registram a condição observada. |

### Dependência de infraestrutura HTTP

O build instala microservice-toolkit por caminho relativo em packages/microservice-toolkit. A cópia da biblioteca no contexto Docker antecede uv sync. Criar as aplicações pelo factory configura logs, correlação e erros sem alterar os contratos de negócio. Os serviços users e condo configuram o verificador de identidade para suas rotas privadas.

O teste de runtime continua exigindo composição de QA isolada na porta publicada pelo ambiente e aceita COMPOSE_PROJECT_NAME para selecionar o ambiente descartável. Os testes de integração ficam dentro de services/apartments/tests/integration.
