# Contrato de verificação — F05 — Cadastro de áreas comuns

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F05-01** (P0D, cobre F05-AC01) — Um administrador cria área com taxa zero. Cadastrar a área, abrir o catálogo do morador e comparar `fee_cents` com a indicação visual -> A área aparece no catálogo como gratuita. Modo: Base.
- **E2E-F05-02** (P0D, cobre F05-AC02) — Uma taxa negativa no cadastro ou na edição. Enviar valores inválidos e consultar a área no catálogo depois -> A requisição é rejeitada e a taxa existente permanece. Modo: Base.
- **E2E-F05-03** (P0D, cobre F05-AC03) — Um morador tenta editar uma taxa. Autenticar como morador, tentar PATCH na rota administrativa e consultar o catálogo -> A operação é recusada e a resposta seguinte preserva o valor. Modo: Base.
- **E2E-F05-04** (P0D, cobre F05-AC04) — Uma área referenciada e uma área recém-criada sem uso. Executar as duas exclusões, comparar catálogo e consultar agenda da área referenciada -> A primeira exclusão é recusada e a segunda remove o cadastro independente. Modo: Base.
- **E2E-F05-05** (P0D, cobre F05-SEC01) — Um cliente sem sessão válida tenta ler ou administrar o catálogo. Consultar as rotas de catálogo e administração sem bearer -> A API recusa o acesso autenticado sem revelar detalhes internos. Modo: Base.
- **E2E-F05-06** (P0D, cobre NFR01-AC01) — Dado QA_AREA existe com fee_cents=100 e QA_A é resident; quando enviar PATCH /api/admin/areas/{QA_AREA} com fee_cents=200 usando QA_A e reler como QA_ADMIN -> Então HTTP 403 e taxa original 100 preservada. Modo: Base: HTTP real.
- **E2E-F05-07** (P0D, cobre NFR02-AC01) — Dado QA_AREA foi criada por QA_ADMIN com fee_cents=100; quando reiniciar common-areas e condo-db sem restore e consultar GET /api/admin/areas/{QA_AREA} -> Então HTTP 200 com o mesmo id, nome e taxa 100, sem segunda área. Modo: Base: HTTP real e reinício.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F05-01 | F05-AC01 | Base |
| E2E-F05-02 | F05-AC02 | Base |
| E2E-F05-03 | F05-AC03 | Base |
| E2E-F05-04 | F05-AC04 | Base |
| E2E-F05-05 | F05-SEC01 | Base |
| E2E-F05-06 | NFR01-AC01 | Base |
| E2E-F05-07 | NFR02-AC01 | Base |
