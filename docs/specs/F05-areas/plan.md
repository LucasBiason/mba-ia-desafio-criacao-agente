# Plano de implementação — F05 — Cadastro de áreas comuns

## Dependências


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
