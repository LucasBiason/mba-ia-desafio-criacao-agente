# Arquitetura — Residencial Aurora

> Estado: arquitetura implementada da base administrativa; revisão de fechamento em andamento.
> Escopo: administração manual, consultas autenticadas e fronteira já existente; arquitetura interna do agente será definida posteriormente.
> Fontes: [PRD](../prd/index.md), [Compose](../../compose.yaml) e [specs](../specs/index.md).

## 1. Objetivo e limites

Organizar as APIs em serviços com responsabilidade explícita e camadas verificáveis. Cada operação percorre router, controller, validators, repository ORM e serializer, após autenticação pelo middleware. Os contratos HTTP usados pelo frontend são preservados. A implementação da consultoria ADK/Gemini e o adaptador acadêmico de F10 continuam pendentes.

## 2. Arquitetura geral

As visões [C1 e C2](c4-context.md) distinguem o limite do sistema das aplicações executáveis. O [modelo conceitual](data-model.md) detalha identidades, cardinalidades e histórico. O blueprint do agente e uma eventual fila não integram a topologia decidida desta etapa.

O portal React é servido pelo Nginx, que encaminha cada recurso ao serviço proprietário. Há oito aplicações FastAPI independentes, dois bancos PostgreSQL e o frontend. O toolkit configura infraestrutura HTTP, enquanto cada aplicação define seu domínio.

As aplicações e os armazenamentos estão na visão [C2](c4-context.md#c2-aplicações-e-persistência).

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
---
title: Requisição privada, identidade e integridade
---
sequenceDiagram
    actor U as Usuário
    participant M as Middleware
    participant A as Autenticação
    participant R as Router
    participant C as Controller
    participant V as Validator
    participant P as Repository ORM
    participant S as Serializer
    U->>M: Request com bearer
    M->>A: Introspecção por HTTP interno
    alt Sessão inválida ou dependência indisponível
        A-->>M: Recusa ou falha de dependência
        M-->>U: 401 ou 503, sem executar a operação
    else Identidade válida
        A-->>M: Conta e papel confiáveis
        M->>R: Request com identidade
        R->>C: DTO e contexto autenticado
        C->>V: Validar permissão e regras
        V->>P: Consultar estado e vínculos
        P-->>V: Estado persistido
        alt Regra ou permissão recusada
            V-->>C: Erro de domínio
            C-->>R: Recusa sem gravação
            R-->>U: 403, 404 ou 422
        else Operação permitida
            V-->>C: Validação concluída
            C->>P: Persistir o modelo em transação
            alt Colisão ou falha de persistência
                P-->>C: Rollback
                C-->>R: Conflito ou indisponibilidade
                R-->>U: 409 ou 503
            else Persistência confirmada
                P-->>C: Objeto ORM
                C->>S: Serializar campos públicos
                S-->>C: DTO de saída
                C-->>R: Resultado tipado
                R-->>U: Response HTTP
            end
        end
    end
~~~

Controllers não executam SQL. Validators não escrevem no banco. Repositories abrangem a transação e convertem alterações de objetos em persistência ORM. Constraints e locks mantêm as invariantes sob concorrência.

## 5. Modelo de dados conceitual

Conta e sessão de login pertencem à identidade. O código interno da unidade é estável e seu número é único. Uma relação associa no máximo um responsável a cada unidade. Uma conta pode responder por várias unidades. Reservas e autorizações preservam o titular original após uma troca de responsável.

O [ER conceitual](data-model.md) representa as cardinalidades e explicita as relações lógicas entre bancos.

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

| Decisão | Origem | Estado | ADR |
| --- | --- | --- | --- |
| Serviços por domínio e camadas | Recorte estrutural do produto e F01 | accepted | [ADR-0001](../adr/ADR-0001-servicos-por-dominio-e-camadas.md) |
| ORM e integridade transacional | Padrão de persistência e F01/F07 | accepted | [ADR-0002](../adr/ADR-0002-orm-e-integridade-transacional.md) |
| Identidade central e permissão por recurso | F03/F04 e vínculos F02 | accepted | [ADR-0003](../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md) |
| Toolkit e operação reproduzível | F01 e padrão operacional do produto | accepted | [ADR-0004](../adr/ADR-0004-toolkit-e-operacao-dos-servicos.md) |
| Regulamento único e versões imutáveis | F06 | accepted | [ADR-0005](../adr/ADR-0005-regulamento-unico-versionado.md) |
| Dois bancos nesta etapa | Topologia observada; confirmação específica pendente | proposed | [ADR-0006](../adr/ADR-0006-persistencia-compartilhada-da-base.md) |

| Risco ou pendência | Impacto | Mitigação ou próxima decisão | Fonte |
| --- | --- | --- | --- |
| Banco de condomínio compartilhado | Acopla migrações e disponibilidade dos serviços | Preservar domínio dos repositories; decidir separação física antes de uma migração própria | ADR-0006 |
| Introspecção central indisponível | APIs privadas deixam de operar | Falhar fechado, readiness e erro de dependência sem mutação | F03 |
| Leituras e edições concorrentes | Podem gerar duplicidade ou perda de alteração | Constraints, locks e versão na transação, com recusa explícita | F02/F04/F05/F06 |
| Agente ainda sem integração | Não cria reservas/autorizações nem confirma ações | Blueprint e implementação posterior; preservar casos futuros como pendentes | F07–F10 |
| Processamento assíncrono sugerido | Acrescenta confirmação, idempotência e retomada a definir | Discutir no blueprint; fila não substitui exclusividade no armazenamento | Enunciado, garantia 5 |

### Verificações realizadas

As fontes são os modelos, repositories, composição, rotas, specs e PRD versionados. O PRD e os quatorze pacotes de specs têm verificação estrutural estrita. Os links locais e os estados dos seis ADRs foram conferidos. As cinco figuras Mermaid foram renderizadas localmente; capturas, resultados de testes e avaliação permanecem externamente ao repositório. A documentação não concede aceite humano nem afirma que as integrações futuras estão implementadas.

### Handoff para especificação

F01–F06 e F11–F14 usam os ADRs da base; F07/F08 distinguem consultas e horários das mutações futuras pelo agente. F09 preserva sessões e fronteira de indisponibilidade. F10 mantém o contrato acadêmico para etapa posterior. O blueprint futuro deve mapear agente principal, especialistas, tools, sessão, confirmação e exclusividade conforme o enunciado, antes de escolher mecanismo de fila, se aplicável.
