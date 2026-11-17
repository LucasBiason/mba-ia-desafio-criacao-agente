# Plano de implementação — F02 — Cadastro de apartamentos

## Dependências


## Passos de implementação

### SI02.1 — Importar e proteger o cadastro de unidades

- Tipo: infraestrutura.
- Depende de: F04 disponível.
- Ações: Criar persistência com código persistente, número único e relação opcional com um usuário morador. Importar os dados e consultar o usuário por fronteira interna.
- Testes: Provar duplicidade, validade do vínculo, exclusão protegida, idempotência da carga e código estável após renumeração.
- Critérios: F02-AC02, F02-AC04, F02-AC05.

### SI02.2 — Ligar gestão e seleção pelo morador

- Tipo: comportamento.
- Depende de: SI02.1.
- Ações: Servir contatos por id público, operações de cadastro e consulta própria com autorização em cada rota.
- Testes: Exercitar duas unidades para um morador e os casos negativos de outra conta e rota administrativa.
- Critérios: F02-AC01, F02-AC03, F02-SEC01.

### SI02.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para cadastro de apartamentos.
- Testes: Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas.
- Critérios: NFR01-AC01, NFR03-AC01.
