# Decisões arquiteturais

Registros produzidos por sdd-design-docs. As escolhas explicitamente definidas no produto são accepted; a decisão retroativa de persistência física permanece proposed. O blueprint do agente e eventual fila ainda não foram decididos.

| ID | Decisão | Estado | Feature |
| --- | --- | --- | --- |
| ADR-0001 | [Separar os serviços por domínio e aplicar camadas](ADR-0001-servicos-por-dominio-e-camadas.md) | accepted | F01 |
| ADR-0002 | [Persistir por ORM com integridade na transação](ADR-0002-orm-e-integridade-transacional.md) | accepted | F01 |
| ADR-0003 | [Centralizar identidade JWT e autorizar por recurso](ADR-0003-identidade-central-e-autorizacao-por-recurso.md) | accepted | F03 |
| ADR-0004 | [Compartilhar infraestrutura HTTP e padronizar a operação](ADR-0004-toolkit-e-operacao-dos-servicos.md) | accepted | F01 |
| ADR-0005 | [Manter um regulamento vigente com versões imutáveis](ADR-0005-regulamento-unico-versionado.md) | accepted | F06 |
| ADR-0006 | [Preservar provisoriamente os dois bancos da base](ADR-0006-persistencia-compartilhada-da-base.md) | proposed | F01 |
