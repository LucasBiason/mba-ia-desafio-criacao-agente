# Contrato de verificação — F13 — Visão geral do morador

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F13-01** (P0D, cobre F13-AC01) — Morador vinculado a uma unidade; abrir o portal e selecionar a unidade -> o resumo usa somente as reservas e visitas permitidas para essa identidade. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F13-02** (P0D, cobre F13-AC02) — Morador sem unidade vinculada; abrir a visão geral -> o estado vazio explica o vínculo necessário e não apresenta dados de terceiros. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F13-03** (P0D, cobre F13-SEC01) — Tentar acesso direto sem a permissão exigida -> Parâmetro de apartamento de outra conta é recusado pelo servidor. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F13-04** (P0D, cobre NFR01-AC01) — Dado QA_A só está vinculado a 9101; quando solicitar GET /api/resident/reservations?apartment=9102 e GET /api/resident/visits?apartment=9102 com QA_A -> Então ambas retornam 403 e o painel não apresenta dados de 9102. Modo: Portal e API reais.

- **E2E-F13-05** (P0D, cobre NFR03-AC01) — Dado 9101 tem QA_RES_A e 9102 tem QA_RES_B; quando abrir #/inicio como QA_A, selecionar 9101 e inspecionar respostas de reservas e visitas -> Então resumo contém somente registros de QA_A/9101, sem QA_RES_B, nomes alheios ou credenciais. Modo: Portal e API reais.

## Cobertura

Cada item P0D corresponde ao critério funcional ou de segurança identificado no requisito e na matriz de testes da spec. Casos de privacidade e autorização usam as APIs reais com contas de papéis distintos.
