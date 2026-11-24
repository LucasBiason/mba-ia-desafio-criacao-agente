# Contrato de verificação — F12 — Visão geral administrativa

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F12-01** (P0D, cobre F12-AC01) — Uma conta administrativa e dados carregados; abrir a visão geral -> o painel mostra totais de apartamentos, áreas e reservas coerentes com as APIs. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F12-02** (P0D, cobre F12-AC02) — Painel administrativo aberto; selecionar um atalho de cadastro ou agenda -> a rota correspondente abre e o menu identifica o destino ativo. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F12-03** (P0D, cobre F12-SEC01) — Tentar acesso direto sem a permissão exigida -> Morador não obtém os dados administrativos ao solicitar diretamente suas APIs. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F12-04** (P0D, cobre NFR01-AC01) — Dado QA_A é resident; quando solicitar GET /api/admin/apartments, /api/admin/areas e /api/admin/reservations com QA_A -> Então as três chamadas retornam 403 sem totais ou registros administrativos. Modo: Portal e API reais.

- **E2E-F12-05** (P0D, cobre NFR03-AC01) — Dado QA_ADMIN tem o painel aberto com massa sintética; quando comparar cards com GET /api/admin/apartments, /api/admin/areas e /api/admin/reservations e inspecionar os corpos -> Então contagens coincidem e nenhuma projeção contém senha, hash ou bearer. Modo: Portal e API reais.

## Cobertura

Cada item P0D corresponde ao critério funcional ou de segurança identificado no requisito e na matriz de testes da spec. Casos de privacidade e autorização usam as APIs reais com contas de papéis distintos.
