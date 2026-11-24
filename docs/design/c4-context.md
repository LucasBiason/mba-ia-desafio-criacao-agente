# Contexto e aplicações — Residencial Aurora

Público: desenvolvimento e revisão. As visões respondem quem usa o sistema e quais processos atendem ao portal e à avaliação. Fontes: [PRD](../prd/index.md), [composição](../../configs/compose.yaml), [gateway do portal](../../services/frontend/nginx.conf) e [ADRs](../adr/README.md).

## C1 — limite do sistema

```mermaid
---
title: Residencial Aurora — c4-context 1
---
flowchart LR
    ADMIN["Administração"] -->|"Gerencia o condomínio"| AURORA["Residencial Aurora"]
    RESIDENT["Morador"] -->|"Consulta e solicita ações autorizadas"| AURORA
    EVAL["Avaliador local"] -->|"Executa as seis rotas do assistente"| AURORA
    AURORA -->|"Intenções e trechos necessários via HTTPS"| GEMINI["Gemini · Google AI Studio"]
```

A administração mantém contas, apartamentos, áreas, regulamento e horários; o morador acessa suas unidades e o assistente. O avaliador usa a interface do assistente isolada. O operador prepara o ambiente por Makefile/Compose. Pagamentos reais e deploy público não integram esta arquitetura.

## C2 — aplicações e persistência

| Aplicação ou armazenamento | Responsabilidade e fronteira |
| --- | --- |
| Frontend React/Nginx | Interface e roteamento autenticado na mesma origem |
| auth e users | Identidade, JWT, contas e introspecção interna |
| apartments e common-areas | Unidades, responsáveis e catálogo de áreas |
| agenda, visits e parameters | Reservas, autorizações e revisões do regulamento |
| agent | Sessões do morador, contexto, histórico e tools autorizadas |
| Gateway e aplicação do assistente | Contrato local do avaliador, turnos ADK e confirmações |
| PostgreSQL de identidade | Contas e sessões de login do portal |
| PostgreSQL de condomínio | Cadastros, domínio e estado de conversa do produto |
| Persistência ADK do portal | Sessões/eventos do runtime do assistente |
| PostgreSQL do assistente | Domínio, pendências, recibos e sessões/eventos do assistente |
| Jobs de preparação | Schema atual, fixtures e recursos antes dos servidores |

```mermaid
---
title: Residencial Aurora — c4-context 2
---
flowchart TB
    BROWSER["Navegador"] -->|"HTTP autenticado"| WEB["Frontend · React/Nginx"]
    WEB -->|"Login e perfil"| AUTH["auth"]
    WEB -->|"Gestão de contas"| USERS["users"]
    WEB -->|"Cadastros e agenda"| DOMAINS["apartments · common-areas<br/>agenda · visits · parameters"]
    WEB -->|"Sessão e conversa"| AGENT["agent · ADK"]
    USERS -->|"SQLAlchemy"| IDDB[("PostgreSQL identidade")]
    AUTH -->|"SQLAlchemy"| IDDB
    DOMAINS -->|"SQLAlchemy"| CONDODB[("PostgreSQL condomínio")]
    DOMAINS -->|"Introspecção HTTP interna"| AUTH
    AGENT -->|"Introspecção HTTP interna"| AUTH
    AGENT -->|"SQLAlchemy · dados autorizados, histórico e admissão"| CONDODB
    AGENT -->|"Sessões e eventos"| ADKDB[("SQLite · ADK portal")]
    AGENT -->|"HTTPS"| GEMINI["Gemini"]
    EVALUATOR["Avaliador · localhost:8000"] -->|"HTTP local"| GATEWAY["Gateway do assistente"]
    GATEWAY -->|"HTTP local"| ACADEMIC["API do assistente · FastAPI/ADK"]
    ACADEMIC -->|"ORM e ADK · turnos, domínio e eventos"| AGENTDB[("PostgreSQL do assistente")]
    ACADEMIC -->|"HTTPS"| GEMINI
```

A aplicação acadêmica é executada em duas réplicas no Compose; essa escolha de implantação compartilha o mesmo banco, sem alterar as fronteiras C2.

Os gateways e armazenamentos mantêm separadas as superfícies do assistente e do portal. A API do assistente não usa o banco do portal. O contexto do modelo é vinculado à sessão pelo servidor. A exclusividade da reserva é imposta no armazenamento compartilhado pelas réplicas.

Os toolkits são dependências Python das aplicações: `microservice-toolkit` fornece infraestrutura; `aurora-toolkit`, convenções de identidade e domínio do cluster. Não são processos HTTP. Os preparadores finitos criam o schema atual e importam dados ausentes; não restauram volumes em uma partida normal. A operação e os fluxos estão na [arquitetura](architecture.md).
