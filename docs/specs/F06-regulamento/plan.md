# Plano de implementação — F06 — Regulamento único e versionado

## Dependências

Entradas: [requisito do PRD](../../prd/functional/F06-regulamento.md), [spec](spec.md) e [arquitetura](../../arquitetura.md). Dependências de produto: F03. Os passos que dependem das atividades de agentes seguem o [roteiro separado](../../roteiro-agente.md). A execução observada é registrada em [validação](../../validacao.md).

## Passos de implementação

### SI06.1 — Registrar versões e impedir edição concorrente

- Tipo: infraestrutura.
- Depende de: F03 disponível.
- Ações: Importar versão zero, criar armazenamento imutável e publicar sob comparação com versão-base.
- Testes: Publicar uma edição, repetir com base antiga e consultar histórico antes e depois do reinício.
- Critérios: F06-AC01, F06-AC02, F06-AC04.

### SI06.2 — Conectar editor, histórico e leitura vigente

- Tipo: comportamento.
- Depende de: SI06.1.
- Ações: Implementar telas por papel e tratar conteúdo editado como texto, incluindo recuperação do conflito.
- Testes: Exercitar edição admin, leitura residente e bloqueio à escrita e histórico por morador.
- Critérios: F06-AC03, F06-SEC01.

### SI06.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para regulamento único e versionado.
- Testes: Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas.
- Critérios: NFR02-AC01, NFR03-AC01.

## Execução observada dos passos

O plano descreve a decomposição esperada. A existência do código permite identificar implementação, mas não comprova execução histórica SI por SI. Os passos de Base têm implementação referenciada na spec e evidências anteriores em validação. Passos de Aula do agente e Avaliação acadêmica continuam pendentes. Revisão independente, aceite humano por critério e integração Git devem ser registrados antes do fechamento.
