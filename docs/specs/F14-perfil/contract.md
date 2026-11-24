# Contrato de verificação — F14 — Consulta do próprio perfil

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F14-01** (P0D, cobre F14-AC01) — Uma conta autenticada; selecionar o nome na barra superior -> a tela Meu perfil apresenta nome, e-mail e tipo da identidade autenticada. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F14-02** (P0D, cobre F14-AC02) — Sessão encerrada; tentar abrir a rota de perfil -> o portal volta à entrada e a API privada recusa a sessão revogada. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F14-03** (P0D, cobre F14-SEC01) — Tentar acesso direto sem a permissão exigida -> O perfil é obtido da identidade autenticada, sem aceitar um ID arbitrário da interface. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F14-04** (P0D, cobre NFR01-AC01) — Dado A sessão QA_A foi revogada por POST /api/auth/logout; quando reutilizar o bearer revogado em GET /api/auth/me e abrir #/perfil -> Então API retorna 401 INVALID_SESSION e o portal retorna à entrada sem perfil. Modo: Portal e API reais.

- **E2E-F14-05** (P0D, cobre NFR03-AC01) — Dado QA_A e QA_ADMIN estão autenticados em contextos de navegador separados; quando consultar GET /api/auth/me e abrir #/perfil em cada contexto -> Então nome, email e papel coincidem com a própria identidade; respostas excluem password_hash e dados da outra conta. Modo: Portal e API reais.

## Cobertura

Cada item P0D corresponde ao critério funcional ou de segurança identificado no requisito e na matriz de testes da spec. Casos de privacidade e autorização usam as APIs reais com contas de papéis distintos.
