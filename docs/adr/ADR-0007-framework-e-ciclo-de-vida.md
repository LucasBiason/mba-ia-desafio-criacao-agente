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

A pasta services representa serviços de negócio. Infraestrutura genérica pertence ao toolkit; tipos e identidade do residencial pertencem ao aurora-toolkit. A aplicação HTTP precisa iniciar sem executar DDL nem carregar fixtures.

Origem: [arquitetura](../design/architecture.md), [F01](../specs/F01-fundacao/spec.md) e o recorte de separação definido para o produto. Este registro detalha os limites dos ADRs 0001 e 0004; mantém as fronteiras de persistência aceitas no ADR-0006.

## Opções consideradas

- Framework genérico com submódulos e pacote Aurora separado, opção escolhida.
- Helpers e infraestrutura em services/persistence e no topo de services, organização rejeitada.

## Resultado da decisão

O microservice-toolkit fornece aplicação, lifespan, autenticação de transporte, erros, health, observabilidade, ORM, schemas e cliente HTTP. Não conhece modelos nem nomes do residencial. O aurora-toolkit contém tipos, permissões, protocolo de identidade e convenções de dados do cluster. Cada serviço mantém seus modelos, regras e bootstrap.py.

REQUIRED_SECRETS declara nomes de variáveis para validação pelo lifespan genérico. Os main.py não repetem lifecycle nem inicialização de banco. /health é liveness; uma eventual /ready é separada e opcional. identity-init e condo-init preparam o portal; a preparação explícita do agente inclui sessões/eventos ADK, projeção de histórico, ledger e admissão. agent-init prepara o banco da API do desafio. Todos concluem antes dos respectivos servidores. Tabelas existentes não são recarregadas nem alteradas pela partida HTTP.

### Consequências

- Positiva: responsabilidades verificáveis e infraestrutura reutilizável sem dependência do residencial.
- Negativa: a composição precisa coordenar preparação e servidores; um schema existente incompatível exige procedimento específico fora da partida HTTP.
- Neutra: a inicialização usa o esquema atual e mantém os dados existentes, sem remover tabelas ou volumes antigos.

### Confirmação

Validar imports e dependências dos pacotes, o ciclo de vida sem acesso ao banco, liveness com banco indisponível, preparação repetida sem mutação e o fluxo autenticado administrador→apartments em uma composição isolada.
