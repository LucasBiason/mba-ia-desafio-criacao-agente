<div align="center">
  <img src="branding/banner.svg" alt="Residencial Aurora — Regra é regra" width="100%" />
  <br /><br />
  <img src="branding/logo.svg" alt="Logo do Residencial Aurora" width="88" />
</div>

# Residencial Aurora

Assistente virtual para reservar áreas comuns, cancelar reservas do próprio apartamento, autorizar visitantes e consultar o regulamento do condomínio. Projeto do desafio **Regra é regra**, do MBA de IA da Full Cycle.

![Python 3.12 ou superior](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-depend%C3%AAncias-6340AC?style=flat-square&logo=uv&logoColor=white)
![Google ADK série 2](https://img.shields.io/badge/Google_ADK-s%C3%A9rie_2-4285F4?style=flat-square&logo=google&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-modelo-5268D6?style=flat-square&logo=googlegemini&logoColor=white)

**Status:** base administrativa e portal implementados. A integração Google ADK/Gemini e o protocolo acadêmico estão pendentes.

## Arquitetura

A proposta inclui frontend, backend do condomínio e serviços de autenticação, usuários e agente, com Docker Compose para o ambiente local. O produto usa JWT e permissões por papel e apartamento. O modo local do avaliador mantém o contrato oficial na porta 8000. Um agente principal encaminha as solicitações para especialistas de reservas, visitantes e regulamento. As tools usam o apartamento vinculado à sessão para consultar dados e executar operações.

## Garantias

A implementação será avaliada por cinco comportamentos.

1. Reservas pagas e autorizações de visitantes só produzem efeito após aprovação pela rota de confirmações.
2. Cada sessão acessa os dados do apartamento associado na criação.
3. Conversas, eventos e alterações persistem após reiniciar a API.
4. A consulta ao regulamento traz ao contexto apenas trechos pertinentes.
5. A exclusividade por área e data é garantida na gravação, inclusive sob concorrência.

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

A entrega atual é a base administrativa manual. Criar/cancelar reservas e autorizar visitantes pelo agente, confirmações e modo acadêmico são a próxima etapa do desafio. O [PRD](docs/prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) delimita os critérios atuais e posteriores.

## Documentação

- [Enunciado oficial](docs/enunciado.md)
- [Contrato da API](docs/enunciado.md#contrato-da-api)
- [Fluxo do avaliador](docs/enunciado.md#fluxo-do-avaliador)
- [PRD](docs/prd/index.md)
- [Dados iniciais do condomínio](dados/)

## Fluxos do portal

- A administração cadastra usuários dos tipos Administração e Morador, além de apartamentos e áreas.
- Em **Agenda**, use o mês atual para ver todas as áreas ou filtre por uma delas. Clique no dia para abrir suas reservas, ou busque pelo código para ir direto à área e à data. A administração pode registrar os horários da reserva. O morador consulta os registros da sua unidade.
- Em **Visitas**, a administração pode registrar os horários de entrada e saída.
- A edição do regulamento cria uma nova versão com autor e horário. O histórico mantém a versão anterior. Uma edição iniciada numa versão ultrapassada recebe conflito.
- O morador seleciona a unidade e cria uma sessão persistente em **Assistente**. As mensagens nesse fluxo exibem a pendência da integração do agente.

Os cinco arquivos de dados iniciais ficam em `dados/`. Identidade e condomínio leem a fonte na inicialização. Cada apartamento tem código interno e número. Seu responsável é um único usuário do tipo Morador, que representa também o proprietário neste exercício. Os nomes de `apartamentos.json` alimentam esses usuários e a relação com as unidades. As demais contas importadas começam desativadas e podem ser habilitadas pela administração com uma senha definida no painel. Horários ausentes nos arquivos ficam como **Não informado** até serem preenchidos.

## Especificações e arquitetura

- [PRD do produto](docs/prd/index.md)
- [Specs e planos por feature](docs/specs/index.md)
- [Arquitetura e contratos entre serviços](docs/design/architecture.md)
- [Contexto e aplicações C4](docs/design/c4-context.md)
- [Modelo conceitual](docs/design/data-model.md)
- [ADRs](docs/adr/README.md)

## Reexecutar os testes da base

Na instância local do playground, use `make seed-agenda` para preencher vários meses do calendário com reservas sintéticas. Cada uma aparece com a indicação **Teste**. Use `make unseed-agenda` para retirar a massa gerada e voltar aos registros anteriores.

Os testes que alteram dados usam por padrão a porta 8768, separada da porta de uso 8767. Para outra composição de teste, informe `AURORA_URL` ou `AURORA_TEST_PORT`. Use sempre um projeto Compose separado para deixar os dados de exercício fora da instância de uso:

```sh
COMPOSE_PROJECT_NAME=residencial-aurora-qa AURORA_PORT=8768 make up
COMPOSE_PROJECT_NAME=residencial-aurora-qa AURORA_PORT=8768 make test
COMPOSE_PROJECT_NAME=residencial-aurora-qa AURORA_PORT=8768 make test-runtime
COMPOSE_PROJECT_NAME=residencial-aurora-qa make down
```

Use `make test-unit` para os testes do toolkit e da validação de identidade. A regressão móvel fica em `make test-ui`, com Playwright Python/Chromium instalados e as variáveis `AURORA_URL` e `AURORA_TEST_ADMIN_PASSWORD` fornecidas por um ambiente sintético de teste; `AURORA_TEST_ADMIN_EMAIL` é opcional. O teste não lê nem imprime a configuração pessoal.

Os testes verificam a API servida pelo proxy do portal. O modo de avaliação do desafio e a chamada ao modelo pertencem ao escopo de integração do agente.

## Biblioteca dos serviços

Os serviços usam microservice-toolkit para criar aplicações FastAPI, padronizar erros, propagar X-Request-ID e registrar logs JSON. O pacote fica em packages/microservice-toolkit para que um clone do fork possa construir as imagens sem depender de outro checkout. O serviço de identidade mantém o adaptador específico das APIs do Aurora em services/authentication/client.py.

Os testes de integração do domínio ficam em services/apartments/tests/integration/. A biblioteca independente tem seus próprios testes no projeto microservice-toolkit.

## Importação administrativa

Execute python3 dados/importar_cadastros.py --url http://127.0.0.1:8767 para importar cadastros ausentes de usuários moradores, apartamentos e áreas pelas APIs. A senha administrativa é solicitada no terminal. Registros existentes são conservados. O comando pode ser reexecutado após falha parcial.

Os registros iniciais de reservas, autorizações e regulamento continuam carregados pela inicialização do domínio, preservando as fixtures do desafio. Os endpoints de criação por agente permanecem pendentes.

## Serviços e camadas

As aplicações FastAPI ficam em services/authentication, users, apartments, common_areas, agenda, visits, settings e agent. Cada aplicação tem composição em main.py e camadas de routers, controllers, validators, repositories ORM, models, schemas e serializers. O toolkit registra /health e configura Swagger e OpenAPI.

Cada serviço tem documentação em /services/NOME/docs no portal. Os nomes são auth, users, apartments, common-areas, agenda, visits, settings e agent. Os testes integrados ficam em services/apartments/tests/integration.

Os serviços de negócio usam inicialmente o banco PostgreSQL de condomínio existente para preservar os dados e constraints. A separação física dos bancos por serviço exige uma migração adicional.
