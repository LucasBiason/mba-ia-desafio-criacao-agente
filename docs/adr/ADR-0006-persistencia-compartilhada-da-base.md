---
status: accepted
date: 2026-11-23
decision-makers: [Responsável pelo produto]
source: ../design/architecture.md
source_section: "10. Decisões, riscos e validação"
feature: F01
spec: ../specs/F01-fundacao/spec.md
spec_section: "3. Decisões técnicas"
---

# ADR-0006: Delimitar os armazenamentos de identidade, condomínio e assistente

## Contexto e problema

O cluster local contém duas superfícies com fronteiras distintas: o portal autenticado e a API do desafio. Os serviços do portal precisam compartilhar regras transacionais e consultar identidade sem dar à API local do avaliador acesso a esses dados.

Origem: [arquitetura](../design/architecture.md#10-decisões-riscos-e-validação), [F01](../specs/F01-fundacao/spec.md#3-decisões-técnicas) e configuração de cluster aprovada pelo responsável pelo produto. Este registro descreve a topologia atual do produto.

## Fatores da decisão

Isolamento entre portal e avaliador, coordenação transacional de efeitos locais, persistência após reinício e operação reproduzível em Compose.

## Opções consideradas

- PostgreSQL de identidade, PostgreSQL de condomínio e persistência ADK dedicada para o portal; PostgreSQL separado para a API do desafio: opção escolhida.
- Banco físico por serviço: não integra a topologia deste produto e exigiria decisão e contratos próprios.

## Resultado da decisão

`identity-db` armazena contas e sessões revogáveis de auth/users. `condo-db` armazena apartamentos, áreas, reservas, visitas, revisões, sessões públicas, histórico projetado, confirmações, recibos e admissão do agente do portal. Cada domínio conserva seus models e repositories ORM. Os IDs de identidade cruzam os bancos somente como referências lógicas verificadas pelo servidor, sem foreign key física entre bancos.

O runtime ADK do portal usa SQLite em volume próprio para sessões/eventos. O histórico público é uma projeção persistente limitada por página no banco de condomínio, sem carregar todo o histórico ADK por consulta. Ledger e efeitos locais usam a mesma transação de condomínio; não há transação distribuída por HTTP.

A API do avaliador usa `agent-db`, um terceiro PostgreSQL que contém seu domínio, sessões/eventos ADK, pendências e recibos. As duas réplicas compartilham esse banco e sua rede; não leem nem alteram os dados do portal. SQLite em disco é a alternativa local de processo único para desenvolvimento e testes do contrato acadêmico.

### Consequências

- Positiva: a restauração do assistente fica isolada do portal e as réplicas coordenam exclusividade pelo mesmo armazenamento.
- Negativa: domínios do condomínio compartilham esquema e disponibilidade; o portal mantém duas persistências para conversa pública e eventos ADK.
- Neutra: processos separados não significam autonomia física de dados. Uma mudança dessa fronteira exige uma decisão própria.

### Confirmação

Conferir [Compose](../../configs/compose.yaml), modelos e repositories de cada serviço. Executar em ambiente isolado os contratos F01, F07, F09 e F10 para reinício, isolamento, paginação e disputa. Este ADR não registra resultado de execução nem aceite humano.
