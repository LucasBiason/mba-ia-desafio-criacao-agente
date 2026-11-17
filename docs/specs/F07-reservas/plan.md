# Plano de implementação — F07 — Reservas e agenda por área

## Dependências

Entradas: [requisito do PRD](../../prd/functional/F07-reservas.md), [spec](spec.md) e [arquitetura](../../arquitetura.md). Dependências de produto: F02, F05. Os passos que dependem das atividades de agentes seguem o [roteiro separado](../../roteiro-agente.md). A execução observada é registrada em [validação](../../validacao.md).

## Passos de implementação

### SI07.1 — Publicar agenda e reservas próprias

- Tipo: comportamento.
- Depende de: F02 e F05 disponíveis.
- Ações: Importar o histórico, implementar projeções por papel e filtros e ligar o calendário por área, a busca por código, o registro de horários e a consulta do morador.
- Testes: Comparar APIs e navegação, dias ocupados e busca por código. Exercitar atualização de horários e escopo por papel.
- Critérios: F07-AC01, F07-AC04, F07-AC06, F07-SEC01.

### SI07.2 — Conectar as operações de reserva na aula

- Tipo: comportamento.
- Depende de: SI07.1 e etapas de consulta e confirmação de F09.
- Ações: Acoplar ferramentas tipadas, validar identidade de sessão, aplicar exclusividade transacional e preservar códigos históricos.
- Testes: Provar fluxo gratuito, taxa com pendência, cancelamento próprio e confirmação concorrente.
- Critérios: F07-AC02, F07-AC03, F07-AC05.

### SI07.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para reservas e agenda por área.
- Testes: Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas.
- Critérios: NFR01-AC01, NFR02-AC01, NFR03-AC01.

## Execução observada dos passos

O plano descreve a decomposição esperada. A existência do código permite identificar implementação, mas não comprova execução histórica SI por SI. Os passos de Base têm implementação referenciada na spec e evidências anteriores em validação. Passos de Aula do agente e Avaliação acadêmica continuam pendentes. Revisão independente, aceite humano por critério e integração Git devem ser registrados antes do fechamento.
