# Plano de implementação — F05 — Cadastro de áreas comuns

## Dependências

Entradas: [requisito do PRD](../../prd/functional/F05-areas.md), [spec](spec.md) e [arquitetura](../../arquitetura.md). Dependências de produto: F03. Os passos que dependem das atividades de agentes seguem o [roteiro separado](../../roteiro-agente.md). A execução observada é registrada em [validação](../../validacao.md).

## Passos de implementação

### SI05.1 — Preservar catálogo inicial e integridade das taxas

- Tipo: infraestrutura.
- Depende de: F03 disponível.
- Ações: Importar áreas e estabelecer validações de centavos, chave e exclusões de áreas referenciadas.
- Testes: Exercitar valores negativos, área inexistente, duplicidade e referência histórica.
- Critérios: F05-AC02, F05-AC04.

### SI05.2 — Publicar catálogo autenticado e gestão administrativa

- Tipo: comportamento.
- Depende de: SI05.1.
- Ações: Conectar as telas e aplicar autorização diferente para leitura e mutação.
- Testes: Criar uma área gratuita, conferir status visual e comparar acesso sem sessão e como morador.
- Critérios: F05-AC01, F05-AC03, F05-SEC01.

### SI05.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para cadastro de áreas comuns.
- Testes: Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita.
- Critérios: NFR01-AC01, NFR02-AC01.

## Execução observada dos passos

O plano descreve a decomposição esperada. A existência do código permite identificar implementação, mas não comprova execução histórica SI por SI. Os passos de Base têm implementação referenciada na spec e evidências anteriores em validação. Passos de Aula do agente e Avaliação acadêmica continuam pendentes. Revisão independente, aceite humano por critério e integração Git devem ser registrados antes do fechamento.
