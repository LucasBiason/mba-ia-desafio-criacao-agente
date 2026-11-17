# Plano de implementação — F08 — Autorizações de visita

## Dependências

Entradas: [requisito do PRD](../../prd/functional/F08-visitantes.md), [spec](spec.md) e [arquitetura](../../arquitetura.md). Dependências de produto: F02. Os passos que dependem das atividades de agentes seguem o [roteiro separado](../../roteiro-agente.md). A execução observada é registrada em [validação](../../validacao.md).

## Passos de implementação

### SI08.1 — Importar autorizações e servir as projeções

- Tipo: comportamento.
- Depende de: F02 disponível.
- Ações: Importar nome, data e unidade. Expor consultas por papel e a atualização administrativa dos horários.
- Testes: Abrir as listas como administração e morador e verificar recusa de unidade alheia, salvar horários e validar a sequência de entrada e saída.
- Critérios: F08-AC04, F08-AC05, F08-SEC01.

### SI08.2 — Integrar autorização à confirmação do assistente

- Tipo: comportamento.
- Depende de: SI08.1 e etapa de confirmações de F09.
- Ações: Acoplar tool contextualizada, validar dia e nome e gravar somente depois da aprovação persistida.
- Testes: Exercitar confirmação verbal, aprovação, reinício e tentativa de consulta fora da sessão.
- Critérios: F08-AC01, F08-AC02, F08-AC03.

### SI08.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para autorizações de visita.
- Testes: Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas.
- Critérios: NFR01-AC01, NFR02-AC01, NFR03-AC01.

## Execução observada dos passos

O plano descreve a decomposição esperada. A existência do código permite identificar implementação, mas não comprova execução histórica SI por SI. Os passos de Base têm implementação referenciada na spec e evidências anteriores em validação. Passos de Aula do agente e Avaliação acadêmica continuam pendentes. Revisão independente, aceite humano por critério e integração Git devem ser registrados antes do fechamento.
