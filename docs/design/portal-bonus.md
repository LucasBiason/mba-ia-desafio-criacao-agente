# Portal do Residencial Aurora: bônus de portfólio

Este portal não faz parte dos critérios da avaliação acadêmica. Use a [API acadêmica](../../README.md) para o roteiro oficial.

## Abrir o portal

Com Docker Compose, Make, Python 3 e a partir da raiz do projeto:

```sh
make up
```

Abra [o portal local](http://127.0.0.1:8767/). A primeira execução grava senhas de demonstração geradas no arquivo local `.env`. A instalação usa o mesmo arquivo nas próximas execuções.

| Perfil | E-mail | Senha no arquivo local |
| --- | --- | --- |
| Administração auxiliar | `super@aurora.test` | `DEMO_SUPER_PASSWORD` |
| Administração | `admin@aurora.test` | `DEMO_ADMIN_PASSWORD` |
| Moradora responsável pela unidade 101 | `morador@aurora.test` | `DEMO_RESIDENT_PASSWORD` |

Para consultar os contêineres, use `make ps`. Para parar a instância mantendo os registros, use `make stop`. Use `AURORA_PORT=8780 make up` se quiser outra porta local.


Para desenvolvimento com recarga automática, use `make up ENV=dev`. O Compose base usa o estágio `production` do Dockerfile; o override em `configs/compose.dev.yaml` seleciona `development`, monta o código e usa o comando `dev` do entrypoint. Use o mesmo `ENV` nos comandos seguintes. `make help` lista as operações. `make down` preserva os volumes. Os comandos de teste requerem uv instalado.

O portal mantém o fluxo administrativo manual. A demonstração acadêmica de reservas, visitas e confirmações usa a API local em separado. O [PRD](../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) delimita o escopo do produto.

## Documentação

- [Enunciado oficial](../enunciado.md)
- [Contrato da API](../enunciado.md#contrato-da-api)
- [Fluxo do avaliador](../enunciado.md#fluxo-do-avaliador)
- [Protocolo de confirmação do agente](agent-confirmation-ledger.md)
- [PRD](../prd/index.md)
- [Dados iniciais do condomínio](../../dados/)

## Fluxos do portal

- A administração cadastra usuários dos tipos Administração e Morador, além de apartamentos e áreas.
- Em **Agenda**, use o mês atual para ver todas as áreas ou filtre por uma delas. Clique no dia para abrir suas reservas, ou busque pelo código para ir direto à área e à data. A administração pode registrar os horários da reserva. O morador consulta os registros da sua unidade.
- Em **Visitas**, a administração pode registrar os horários de entrada e saída.
- A edição do regulamento cria uma nova versão com autor e horário. O histórico mantém a versão anterior. Uma edição iniciada numa versão ultrapassada recebe conflito.
- O morador abre **Assistente** para retomar a conversa persistente da sua unidade. No Compose base, o agente com modelo externo fica desabilitado. O perfil de QA com Gemini habilita consultas, reservas, visitas e cartões de confirmação com dados sintéticos; veja [configuração de QA com Gemini](../../compose.portal-gemini.yaml).

Os cinco arquivos de dados iniciais ficam em `dados/`. Identidade e condomínio leem a fonte na inicialização. Cada apartamento tem código interno e número. Seu responsável é um único usuário do tipo Morador, que representa também o proprietário neste exercício. Os nomes de `apartamentos.json` alimentam esses usuários e a relação com as unidades. As demais contas importadas começam desativadas e podem ser habilitadas pela administração com uma senha definida no painel. Horários ausentes nos arquivos ficam como **Não informado** até serem preenchidos.

## Especificações e arquitetura

- [PRD do produto](../prd/index.md)
- [Specs e planos por feature](../specs/index.md)
- [Arquitetura e contratos entre serviços](../design/architecture.md)
- [Contexto e aplicações C4](../design/c4-context.md)
- [Modelo conceitual](../design/data-model.md)
- [ADRs](../adr/README.md)

## Reexecutar os testes da base

Na instância local do playground, use `make seed-agenda` para preencher vários meses do calendário com reservas sintéticas. Cada uma aparece com a indicação **Teste**. Use `make unseed-agenda` para retirar a massa gerada e voltar aos registros anteriores.

Os testes que alteram dados usam por padrão a porta 8768, separada da porta de uso 8767. Para outra composição de teste, informe `AURORA_URL` ou `AURORA_TEST_PORT`. Use sempre um projeto Compose separado para deixar os dados de exercício fora da instância de uso:

```sh
COMPOSE_PROJECT_NAME=residencial-aurora-qa AURORA_PORT=8768 make up
COMPOSE_PROJECT_NAME=residencial-aurora-qa AURORA_PORT=8768 make test
COMPOSE_PROJECT_NAME=residencial-aurora-qa AURORA_PORT=8768 make test-runtime
COMPOSE_PROJECT_NAME=residencial-aurora-qa make down
```

Use `make test-unit` para os testes da validação de identidade da aplicação. Os testes próprios do toolkit pertencem ao projeto original da biblioteca e não acompanham a cópia em packages/. A regressão móvel fica em `make test-ui`, com Playwright Python/Chromium instalados e as variáveis `AURORA_URL` e `AURORA_TEST_ADMIN_PASSWORD` fornecidas por um ambiente sintético de teste; `AURORA_TEST_ADMIN_EMAIL` é opcional. O teste não lê nem imprime a configuração pessoal.

Os testes verificam a API servida pelo proxy do portal. O modo de avaliação do desafio e a chamada ao modelo pertencem ao escopo de integração do agente.

## Biblioteca dos serviços

Os serviços usam microservice-toolkit para criar aplicações FastAPI, padronizar erros, propagar X-Request-ID e registrar logs JSON. O pacote fica em packages/microservice-toolkit para que um clone do fork possa construir as imagens sem depender de outro checkout. O aurora-toolkit mantém o adaptador específico das APIs do Aurora em packages/aurora-toolkit/src/aurora_toolkit/identity.py.

Os testes de integração do domínio ficam em services/apartments/tests/integration/. A biblioteca independente tem seus próprios testes no projeto microservice-toolkit.

## Importação administrativa

Execute python3 tools/importar_cadastros.py --url http://127.0.0.1:8767 para importar cadastros ausentes de usuários moradores, apartamentos e áreas pelas APIs. A senha administrativa é solicitada no terminal. Registros existentes são conservados. O comando pode ser reexecutado após falha parcial.

Os registros iniciais de reservas, autorizações e regulamento continuam carregados pela inicialização do domínio, preservando as fixtures do desafio. O agente do portal é opcional, separado da API acadêmica e não valida a entrega ao avaliador.

## Serviços e camadas

O microservice-toolkit é a infraestrutura genérica, com fábrica em setup_api.py e submódulos auth, middleware, database, models, repository, routers, openapi, exceptions, logging, schemas e services. O aurora-toolkit agrega somente convenções do residencial, tipos de campo, permissões, cliente de identidade e preparação das fontes de dados. Não existe um serviço persistence nem wrappers ApplicationRepository/HealthRepository.

O lifespan do toolkit valida os nomes de segredos declarados em REQUIRED_SECRETS. O /health verifica exclusivamente se a aplicação responde. A preparação inicial usa `make initialize` ou os jobs automáticos de `make up`: identity-init e condo-init. Eles executam os bootstrap.py dos componentes e não alteram tabelas existentes. Não há migração automática de versões legadas.


As aplicações FastAPI ficam em services/authentication, users, apartments, common_areas, agenda, visits, parameters e agent. Cada aplicação tem composição em main.py e camadas de routers, controllers, validators, repositories ORM, models, schemas e serializers. O toolkit registra /health e configura Swagger e OpenAPI.

Cada serviço tem documentação em /services/NOME/docs no portal. Os nomes são auth, users, apartments, common-areas, agenda, visits, parameters e agent. Os testes integrados ficam em services/apartments/tests/integration.

Os serviços de negócio usam inicialmente o banco PostgreSQL de condomínio existente para preservar os dados e constraints. A separação física dos bancos por serviço exige uma migração adicional.

O toolkit incorporado contém somente código e metadados de empacotamento. O lock da raiz governa as dependências do Aurora; README, branding, testes e lock próprios pertencem ao projeto original da biblioteca. A composição base usa SERVICE_ENVIRONMENT=production; o override dev usa development para diagnósticos estruturados. Nunca habilite debug em ambiente público.

### Marco de estudo: roteamento de leitura ADK (opt-in)

`services/agent/runtime/multi_agent_read.py` compõe um principal e especialistas
`reservas`/`convivencia` via transferência nativa (`sub_agents`), na mesma sessão
persistida. Isso preserva eventos de especialistas/tools; a versão AgentTool foi
substituída porque perdia esses eventos em sessão interna em memória. Reservas usa a tool de leitura com
identidade fixa; convivência consulta o regulamento quando a ferramenta é configurada.
Esse marco histórico é só de leitura e não implementa confirmações; as ações do
portal são uma composição separada, habilitada apenas no perfil de QA. Diagrama, código comentado e limites em
[Topologia de leitura](../design/agent-read-topology.md).

A topologia de leitura também aceita `RegulationReadTool` explicitamente: consulta
um artigo pertinente da versão vigente, sem enviar regulamento integral ao modelo.
Seleção conservadora, evidências e limitações em
[Consulta seletiva do regulamento](../design/agent-regulation-excerpts.md).
