# Plano de implementação — F04 — Gestão de usuários e perfis

## Dependências


## Passos de implementação

### SI04.1 — Persistir contas e perfis de acesso

- Tipo: infraestrutura.
- Depende de: F03 disponível.
- Ações: Definir unicidade de email, hash e projeção pública. Aplicar regras de criação, papel definido na criação e proteção da última administração ativa.
- Testes: Exercitar duplicidade, papel fixo e proteção da última administração ativa. Verificar projeção sem segredos.
- Critérios: F04-AC02, F04-AC04, F04-SEC01.

### SI04.2 — Integrar painel e consumo pelo domínio

- Tipo: comportamento.
- Depende de: SI04.1.
- Ações: Conectar formulário administrativo a cadastro e edição e usar o id público no vínculo de apartamento.
- Testes: Criar uma conta pelo painel, autenticar como ela, verificar vínculo e recusas de consulta administrativa.
- Critérios: F04-AC01, F04-AC03.

### SI04.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para gestão de usuários e perfis.
- Testes: Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas.
- Critérios: NFR01-AC01, NFR03-AC01.
