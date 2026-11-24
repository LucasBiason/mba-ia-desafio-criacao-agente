# Contrato de verificação — F11 — Navegação responsiva por perfil

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F11-01** (P0D, cobre F11-AC01) — Um administrador ou morador autenticado; abrir seu portal -> o menu mostra itens correspondentes ao perfil, ícones, nomes acessíveis e estado ativo. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-02** (P0D, cobre F11-AC02) — Uma tela com pelo menos 721 px; recolher e expandir o menu -> o espaço do conteúdo acompanha o menu e todos os links conservam nomes acessíveis. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-03** (P0D, cobre F11-AC03) — Uma tela com até 720 px; abrir o menu, navegar, usar Escape ou tocar fora -> o menu sobreposto fecha, permite navegação por teclado e não ocupa permanentemente o conteúdo. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-04** (P0D, cobre F11-AC04) — Menu aberto em celular; navegar pelo teclado e selecionar uma rota -> o foco fica no diálogo durante a interação e chega ao conteúdo após a seleção. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-05** (P0D, cobre F11-SEC01) — Tentar acesso direto sem a permissão exigida -> API mantém autorização mesmo se o cliente alterar o hash ou o HTML. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-06** (P0D, cobre NFR01-AC01) — Dado QA_A é resident com menu do morador aberto; quando abrir #/admin/usuarios e solicitar GET /api/admin/users com o bearer QA_A -> Então API retorna 403 e nenhum usuário administrativo é exibido. Modo: Portal e API reais.

- **E2E-F11-07** (P0D, cobre NFR03-AC01) — Dado QA_A e QA_ADMIN abrem os respectivos menus; quando inspecionar GET /api/auth/me e nomes acessíveis da navegação em cada sessão -> Então cada menu usa o papel da própria conta, sem senha, bearer ou perfil da outra sessão. Modo: Portal e API reais.

## Cobertura

Cada item P0D corresponde ao critério funcional ou de segurança identificado no requisito e na matriz de testes da spec. Casos de privacidade e autorização usam as APIs reais com contas de papéis distintos.
