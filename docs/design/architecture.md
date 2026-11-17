# Arquitetura — Residencial Aurora

> Estado: arquitetura da base em refatoração por domínio.
> Escopo: portal autenticado, cadastros, consultas e fronteira do agente.
> Fontes: [PRD](../prd/index.md), [Compose](../../compose.yaml) e [specs](../specs/index.md).

## 1. Objetivo e limites

Organizar as APIs em serviços com responsabilidade explícita e camadas verificáveis. Cada operação percorre router, controller, validators, repository ORM e serializer, após autenticação pelo middleware. Os contratos HTTP usados pelo frontend são preservados. A implementação da consultoria ADK/Gemini e o adaptador acadêmico de F10 continuam pendentes.

## 2. Arquitetura geral

O portal React é servido pelo Nginx, que encaminha cada recurso ao serviço proprietário. Há oito aplicações FastAPI independentes, dois bancos PostgreSQL e o frontend. O toolkit configura infraestrutura HTTP, enquanto cada aplicação define seu domínio.

~~~mermaid
flowchart LR
    U["Administração ou morador"] -->|"HTTP"| W["React e Nginx"]
    W -->|"HTTP /api/auth"| A["Autenticação"]
    W -->|"HTTP /api/admin/users"| US["Usuários"]
    W -->|"HTTP apartamentos"| P["Apartamentos"]
    W -->|"HTTP áreas"| AR["Áreas comuns"]
    W -->|"HTTP reservas"| AG["Agenda"]
    W -->|"HTTP visitas"| V["Visitas"]
    W -->|"HTTP regulamento"| C["Configurações"]
    W -->|"HTTP chat"| G["Agente"]
    A -->|"ORM"| I[("PostgreSQL identidade")]
    US -->|"ORM"| I
    P -->|"ORM"| D[("PostgreSQL condomínio")]
    AR -->|"ORM"| D
    AG -->|"ORM"| D
    V -->|"ORM"| D
    C -->|"ORM"| D
    G -->|"ORM sessões"| D
~~~

Os serviços de condomínio compartilham inicialmente o banco existente para preservar IDs, constraints e histórico. Cada repository escreve somente nos modelos do seu domínio. Projeções autorizadas podem consultar vínculos e catálogos necessários no mesmo banco. Separar fisicamente esses bancos exigirá contratos de integração e uma migração própria.

## 3. Componentes e responsabilidades

| Serviço | Responsabilidade | Camadas |
| --- | --- | --- |
| authentication | Login, sessão JWT, introspecção e saída | services/authentication |
| users | Contas, perfis e última administração ativa | services/users |
| apartments | Unidades, códigos estáveis e responsáveis | services/apartments |
| common_areas | Áreas comuns e taxas | services/common_areas |
| agenda | Agenda, consultas de reservas e horários | services/agenda |
| visits | Autorizações existentes e horários de visita | services/visits |
| settings | Regulamento vigente e versões imutáveis | services/settings |
| agent | Sessões do morador e fronteira da consultoria | services/agent |

Cada diretório contém main, routers, controllers, validators, repositories, models, schemas e serializers. main apenas compõe a aplicação. services/persistence fornece a base ORM e o repositório de migração. O pacote microservice-toolkit fornece o ciclo transacional, o factory HTTP, logs, autenticação configurável e erros.

## 4. Fluxos de requisições e dados

~~~mermaid
sequenceDiagram
    actor U as Usuário
    participant R as Router
    participant C as Controller
    participant V as Validator
    participant P as Repository ORM
    participant S as Serializer
    U->>R: Request com identidade validada pelo middleware
    R->>C: DTO de entrada e contexto autenticado
    C->>V: Validar operação e permissão
    V->>P: Consultas necessárias às invariantes
    P-->>V: Estado persistido
    V-->>C: Operação permitida ou erro
    C->>P: Criar, alterar ou excluir modelo
    P-->>C: Objeto ORM após flush
    C->>S: Serializar campos públicos
    S-->>C: DTO de saída
    C-->>R: Resultado tipado
    R-->>U: Response HTTP
~~~

Controllers não executam SQL. Validators não escrevem no banco. Repositories abrangem a transação e convertem alterações de objetos em persistência ORM. Constraints e locks mantêm as invariantes sob concorrência.

## 5. Modelo de dados conceitual

Conta e sessão de login pertencem à identidade. O código interno da unidade é estável e seu número é único. Uma relação associa no máximo um responsável a cada unidade. Uma conta pode responder por várias unidades. Reservas e autorizações preservam o titular original após uma troca de responsável.

~~~mermaid
erDiagram
    CONTA ||--o{ SESSAO_LOGIN : estabelece
    CONTA ||--o{ RESPONSABILIDADE : assume
    UNIDADE ||--o| RESPONSABILIDADE : atribui
    UNIDADE ||--o{ RESERVA : possui
    AREA ||--o{ RESERVA : recebe
    UNIDADE ||--o{ AUTORIZACAO : registra
    UNIDADE ||--o{ SESSAO_CHAT : delimita
    CONTA ||--o{ SESSAO_CHAT : inicia
    CONTA |o--o{ VERSAO_REGULAMENTO : publica
~~~

O regulamento tem versão zero importada e versões posteriores com conteúdo, autor e horário. Reservas ativas têm exclusividade de área e data. Horários opcionais respeitam os intervalos validados. Os modelos SQLAlchemy mantêm nomes e chaves das tabelas existentes.

## 6. Interfaces e integrações

As rotas públicas do portal conservam os caminhos de F01–F14. Nginx encaminha usuários, apartamentos, áreas, reservas, visitas, configurações e chat aos respectivos serviços. A introspecção e a consulta interna de usuários exigem credencial de serviço e permanecem fora do proxy público.

Cada aplicação expõe /health pelo toolkit e /docs e /openapi.json por FastAPI. A prontidão consulta o banco pelo HealthRepository. As páginas Swagger ficam acessíveis em /services/auth/docs, /services/users/docs, /services/apartments/docs, /services/common-areas/docs, /services/agenda/docs, /services/visits/docs, /services/settings/docs e /services/agent/docs.

## 7. Escala e disponibilidade

A execução alvo é Docker Compose local. Não há meta aprovada de carga ou disponibilidade de produção. A consulta de identidade é síncrona e sua falha bloqueia APIs privadas. Repositories têm sessões por operação, rollback e fechamento garantidos. Readiness cria uma sessão nova por verificação.

## 8. Segurança e privacidade

O middleware autentica e os validators autorizam ações e recursos. Schemas validam formato e limites antes do controller. Serializers e response_model delimitam a saída pública. Senhas são armazenadas com Argon2 e nunca são devolvidas pelo serializer.

Logs registram serviço, método, template de rota, status, duração e correlação. Erros inesperados não revelam payloads ou traceback. Os modelos preservam constraints de integridade, a última administração ativa e a titularidade histórica.

## 9. Observabilidade e operação

O Makefile oferece setup, config, build, up, stop, down, ps, logs e testes. make up prepara configuração local e sobe a composição. O Dockerfile tem estágios development e production, com entrypoint único que despacha dev/runserver, prod e test usando exec. O override configs/compose.dev.yaml habilita recarga automática e montagem de código; a composição base mantém a imagem imutável. A preparação idempotente fica em configs/setup_local.py e a massa sintética em dados/seed_agenda.py. Não existe pasta scripts na raiz. Cada serviço publica Swagger, OpenAPI e health. O toolkit propaga X-Request-ID nas chamadas entre serviços. A subida normal preserva os volumes e as migrações são transacionais.

O SchemaRepository usa ORM nas cargas e transformações de dados. DDL fica restrito a criação e alteração de esquema. O importador em dados/importar_cadastros.py usa APIs administrativas para cadastros ausentes. A geração removível de reservas de teste usa um repository ORM próprio da agenda.

## 10. Decisões, riscos e validação

| Decisão | Origem | Consequência |
| --- | --- | --- |
| Camadas router, controller, validators, repository e serializer | Padrão de desenvolvimento solicitado | Regra explícita na guideline FastAPI e nos gabaritos da sdd-spec |
| Serviços separados por domínio | Recorte solicitado para o produto | Gateway conserva contratos enquanto processos têm responsabilidades próprias |
| SQLAlchemy para as escritas | Preferência explícita do usuário | CRUD de aplicação e transformações de dados usam ORM |
| Health compartilhado e Swagger por serviço | Requisito de operação solicitado | Factory oferece infraestrutura e aplicação fornece a prontidão |
| Dois bancos existentes nesta etapa | Preservação da base já usada | Separação física adicional requer migração e desenho de integração |

As migrações precisam ser verificadas em uma instalação limpa e sobre volumes anteriores. Os contratos das specs cobrem recusas, concorrência, reinício e saída pública. A consultoria com ADK/Gemini permanece uma capacidade pendente.
