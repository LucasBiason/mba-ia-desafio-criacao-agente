# Contexto e aplicações — base administrativa

Estas visões C4 respondem quem usa o sistema e quais aplicações atendem a operação manual. Público: desenvolvimento e revisão do produto. Fontes: [PRD](../prd/index.md), [composição](../../compose.yaml), [gateway](../../web/nginx.conf), [ADR-0001](../adr/ADR-0001-servicos-por-dominio-e-camadas.md) e [ADR-0006](../adr/ADR-0006-persistencia-compartilhada-da-base.md). São projeções revisáveis da topologia implementada.

## C1 — limite do sistema

A administração gerencia contas, apartamentos, áreas e regulamento e consulta reservas e visitas. O morador usa consultas restritas aos seus vínculos. Não há provedor de modelos necessário para a base manual.

```mermaid
---
title: C1 — Contexto da base administrativa
---
flowchart LR
    ADMIN["Administração"] -->|"Gerencia dados e consulta agenda por HTTP"| AURORA["Residencial Aurora<br/>Portal e APIs autenticadas"]
    RESIDENT["Morador"] -->|"Consulta dados das unidades vinculadas por HTTP"| AURORA
```

O operador local prepara o ambiente por Makefile/Compose; ele não é um ator de negócio do portal. A integração com Google ADK/Gemini e o adaptador acadêmico pertencem à próxima etapa. O contexto atual não representa uma fila, worker ou modelo como componente já entregue.

## C2 — aplicações e persistência

| Aplicação | Tecnologia | Responsabilidade e fronteira |
| --- | --- | --- |
| Portal e gateway | React e Nginx | Interface, navegação e encaminhamento HTTP na mesma origem |
| Autenticação | FastAPI | Credencial, JWT, sessão revogável e introspecção interna |
| Usuários | FastAPI | Contas, dados públicos e proteção da última administração |
| Apartamentos | FastAPI | Unidades e responsável atual |
| Áreas comuns | FastAPI | Catálogo e taxa |
| Agenda | FastAPI | Projeções de reservas e horários administrativos |
| Visitas | FastAPI | Autorizações existentes e horários |
| Parâmetros | FastAPI | Regulamento vigente e versões |
| Fronteira do agente | FastAPI | Sessões persistidas e indisponibilidade explícita da integração |
| Preparação de identidade | Python, job finito | Cria tabelas e dados iniciais de auth/users antes dos servidores |
| Preparação de condomínio | Python, job finito | Cria tabelas e fontes dos domínios antes dos servidores |
| Identidade | PostgreSQL | Contas e sessões; compartilhado por auth/users |
| Condomínio | PostgreSQL | Unidades, vínculos, áreas, reservas, visitas, regulamento e sessões de chat |

```mermaid
---
title: C2 — Aplicações da base e bancos compartilhados
---
flowchart LR
    USER["Navegador"] -->|"HTTP"| WEB["React e Nginx"]
    subgraph SYSTEM["Residencial Aurora — aplicações"]
        WEB -->|"Login e perfil"| AUTH["auth · FastAPI"]
        WEB -->|"Contas"| USERS["users · FastAPI"]
        WEB -->|"Unidades"| APTS["apartments · FastAPI"]
        WEB -->|"Catálogo"| AREAS["common-areas · FastAPI"]
        WEB -->|"Agenda e horários"| AGENDA["agenda · FastAPI"]
        WEB -->|"Visitas e horários"| VISITS["visits · FastAPI"]
        WEB -->|"Regulamento"| PARAMETERS["parameters · FastAPI"]
        WEB -->|"Sessões"| AGENT["agent · FastAPI<br/>integração futura"]
        AUTH -->|"ORM / PostgreSQL"| IDDB[("Banco identidade")]
        USERS -->|"ORM / PostgreSQL"| IDDB
        APTS -->|"ORM / PostgreSQL"| DB[("Banco condomínio")]
        AREAS -->|"ORM / PostgreSQL"| DB
        AGENDA -->|"ORM / PostgreSQL"| DB
        VISITS -->|"ORM / PostgreSQL"| DB
        PARAMETERS -->|"ORM / PostgreSQL"| DB
        AGENT -->|"ORM de sessões"| DB
        INITID["identity-init · preparação"] -.->|"ORM antes dos servidores"| IDDB
        INITCONDO["condo-init · preparação"] -.->|"ORM antes dos servidores"| DB
    end
```

As sete aplicações consumidoras consultam auth por HTTP interno para verificar identidade antes das operações privadas. Apartamentos também consulta a projeção interna de usuários para validar o responsável. Esses contratos são documentados em F02/F03/F04. O gateway não publica os caminhos internos. A separação de aplicações não implica um banco por serviço.

O microservice-toolkit fornece a infraestrutura Python: ciclo de vida, autenticação de transporte, ORM, logs, correlação, erros e health de liveness. O aurora-toolkit fornece os tipos, permissões e protocolo de identidade do cluster. Os jobs finitos coordenam os bootstrap.py antes de iniciar os servidores, preservando tabelas existentes. O [fluxo de requisição](architecture.md#4-fluxos-de-requisições-e-dados) detalha a ordem das camadas e recusas.
