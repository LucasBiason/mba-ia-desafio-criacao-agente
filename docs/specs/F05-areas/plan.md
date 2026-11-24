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
- Testes: enviar PATCH /api/admin/areas/{QA_AREA} com fee_cents=200 usando QA_A e reler como QA_ADMIN; confirmar que HTTP 403 e taxa original 100 preservada; reiniciar common-areas e condo-db sem restore e consultar GET /api/admin/areas/{QA_AREA}; confirmar que HTTP 200 com o mesmo id, nome e taxa 100, sem segunda área.
- Critérios: NFR01-AC01, NFR02-AC01.
