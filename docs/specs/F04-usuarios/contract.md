# Contrato de verificação — F04 — Gestão de usuários e perfis

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F04-01** (P0D, cobre F04-AC01) — Um administrador autenticado e dados de um novo morador. Criar a conta pelo painel, autenticar, confirmar formato público e vincular unidade -> O cadastro devolve perfil público, aceita login da nova conta e permite vinculá-la. Modo: Base.
- **E2E-F04-02** (P0D, cobre F04-AC02) — O último administrador ativo sofre tentativa de desativação. Em ambiente isolado, desativar as outras contas administrativas e tentar desativar a última -> A operação é recusada e uma conta administrativa continua ativa. Modo: Base.
- **E2E-F04-03** (P0D, cobre F04-AC03) — Um morador com sessão válida tenta acessar outro perfil ou a lista administrativa. Pedir lista administrativa e perfil próprio e inspecionar apenas a identidade autenticada -> A resposta não inclui registros alheios. Modo: Base.
- **E2E-F04-04** (P0D, cobre F04-AC04) — Uma conta existente. Atualizar uma conta criada para o teste, repetir email em segunda conta, desativar e reapresentar token -> Edição persiste e a desativação invalida o acesso; duplicidade é rejeitada. Modo: Base.
- **E2E-F04-05** (P0D, cobre F04-SEC01) — Cadastro, edição e erro de duplicidade. Inspecionar respostas válidas e de erro com credenciais descartáveis -> O JSON e a evidência não incluem senha ou hash. Modo: Base.
- **E2E-F04-06** (P0D, cobre NFR01-AC01) — Dado QA_A é resident e QA_USER é uma conta administrativa criada para o teste; quando enviar PATCH /api/admin/users/{QA_USER} com active=false usando QA_A e consultar a conta como QA_ADMIN -> Então HTTP 403 e conta preservada ativa. Modo: Base: HTTP real.
- **E2E-F04-07** (P0D, cobre NFR03-AC01) — Dado QA_ADMIN lista usuários sintéticos QA_A e QA_B; quando consultar GET /api/admin/users e GET /api/auth/me como QA_A -> Então projeções excluem password_hash e registros de login; me retorna somente QA_A sem dados de QA_B. Modo: Base: HTTP real.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F04-01 | F04-AC01 | Base |
| E2E-F04-02 | F04-AC02 | Base |
| E2E-F04-03 | F04-AC03 | Base |
| E2E-F04-04 | F04-AC04 | Base |
| E2E-F04-05 | F04-SEC01 | Base |
| E2E-F04-06 | NFR01-AC01 | Base |
| E2E-F04-07 | NFR03-AC01 | Base |
