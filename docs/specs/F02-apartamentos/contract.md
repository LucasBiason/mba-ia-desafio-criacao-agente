# Contrato de verificação — F02 — Cadastro de apartamentos

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F02-01** (P0D, cobre F02-AC01) — Um administrador e uma conta moradora ativa e cadastrada. Cadastrar uma unidade, editar uma segunda e consultar a API de unidades com credenciais do morador -> O painel associa duas unidades à mesma conta e ambas aparecem na lista própria do morador. Modo: Base.
- **E2E-F02-02** (P0D, cobre F02-AC02) — Um número já existente. Criar uma unidade, repetir POST com vínculo diferente e comparar o estado obtido por GET -> A tentativa duplicada retorna conflito e preserva a unidade original. Modo: Base.
- **E2E-F02-03** (P0D, cobre F02-AC03) — Um morador autenticado. Tentar criar e editar unidades como morador, em seguida comparar a lista administrativa -> As operações administrativas são recusadas sem persistir alterações. Modo: Base.
- **E2E-F02-04** (P0D, cobre F02-AC04) — Uma unidade usada por reserva ou autorização de visita. Tentar DELETE sobre unidade de fixture com dependência e consultar a unidade e a agenda -> A exclusão é bloqueada e o histórico fica disponível. Modo: Base.
- **E2E-F02-05** (P0D, cobre F02-SEC01) — Uma conta vinculada a uma única unidade. Comparar GET de unidades do morador a duas unidades administrativas -> A consulta pessoal não devolve unidades de outras contas. Modo: Base.
- **E2E-F02-06** (P0D, cobre NFR01-AC01) — Dado QA_A autenticado como resident e apartamento 9101 vinculado a QA_A; quando enviar PATCH /api/admin/apartments/9101 com number=9199 usando QA_A e consultar 9101 como QA_ADMIN -> Então PATCH retorna 403 e a consulta administrativa conserva número e vínculo originais. Modo: Base: HTTP real.
- **E2E-F02-07** (P0D, cobre NFR03-AC01) — Dado 9101 pertence a QA_A e 9102 a QA_B; quando consultar GET /api/resident/apartments com QA_A e inspecionar resposta e log sanitizado -> Então lista contém 9101, não contém 9102 nem campos password_hash, credenciais ou bearer. Modo: Base: HTTP real.
- **E2E-F02-08** (P0D, cobre F02-AC05) — Uma unidade da carga inicial e uma unidade editável. Conferir usuários e apartamentos importados e consultar uma unidade de teste após renumerá-la -> A carga associa o usuário morador da fonte à unidade, e o código da unidade editada se mantém após alterar o número. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F02-01 | F02-AC01 | Base |
| E2E-F02-02 | F02-AC02 | Base |
| E2E-F02-03 | F02-AC03 | Base |
| E2E-F02-04 | F02-AC04 | Base |
| E2E-F02-05 | F02-SEC01 | Base |
| E2E-F02-06 | NFR01-AC01 | Base |
| E2E-F02-07 | NFR03-AC01 | Base |
| E2E-F02-08 | F02-AC05 | Base |
