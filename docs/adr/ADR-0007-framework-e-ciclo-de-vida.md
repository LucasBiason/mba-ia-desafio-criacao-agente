---
status: accepted
date: 2026-11-18
decision-makers: [Responsável pelo produto]
source: ../design/architecture.md
source_section: "10. Decisões, riscos e validação"
feature: F01
spec: ../specs/F01-fundacao/spec.md
spec_section: "3. Decisões técnicas"
---

# ADR-0007: Separar infraestrutura genérica, convenções do cluster e preparação dos dados

## Contexto e problema

A pasta services deve representar serviços de negócio. Infraestrutura compartilhada e convenções do residencial não constituem serviços independentes. A validação de secrets e o health estavam repetidos nos main.py, e a criação de tabelas e o suporte legado estavam misturados a uma classe de repository.

Origem: [arquitetura](../design/architecture.md), [F01](../specs/F01-fundacao/spec.md) e o recorte de separação definido para o produto. Este registro detalha os limites dos ADRs 0001 e 0004; não altera a topologia física de dois bancos, registrada como proposta no ADR-0006.

## Opções consideradas

- Framework genérico com submódulos e pacote Aurora separado, opção escolhida.
- Helpers e infraestrutura em services/persistence e no topo de services, organização rejeitada.

## Resultado da decisão

O microservice-toolkit fornece aplicação, lifespan, autenticação de transporte, erros, health, observabilidade, ORM, schemas e cliente HTTP. Não conhece modelos nem nomes do residencial. O aurora-toolkit contém tipos, permissões, protocolo de identidade e convenções de dados do cluster. Cada serviço mantém seus modelos, regras e bootstrap.py.

REQUIRED_SECRETS declara nomes de variáveis para validação pelo lifespan genérico. Os main.py não repetem lifecycle nem inicialização de banco. /health é liveness; uma eventual /ready é separada e opcional. Dois jobs explícitos criam schema atual e fontes iniciais antes dos servidores. Tabelas existentes não são recarregadas nem alteradas; não há suporte automático a upgrade legado.

### Consequências

- Positiva: responsabilidades verificáveis e infraestrutura reutilizável sem dependência do residencial.
- Negativa: a composição precisa coordenar preparação e servidores; instalações legadas exigem estratégia própria fora deste fluxo.
- Neutra: a inicialização usa o esquema atual e mantém os dados existentes, sem remover tabelas ou volumes antigos.

### Confirmação

Validar imports e dependências dos pacotes, o ciclo de vida sem acesso ao banco, liveness com banco indisponível, preparação repetida sem mutação e o fluxo autenticado administrador→apartments em uma composição isolada.
