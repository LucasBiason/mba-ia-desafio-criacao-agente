# Contrato de verificação — F03 — Autenticação e autorização

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F03-01** (P0D, cobre F03-AC01) — Uma conta ativa com credenciais válidas. Autenticar administrador e morador e consultar o perfil e a superfície privada permitida -> Login devolve uma sessão JWT aceito na leitura privada apropriada ao papel. Modo: Base.
- **E2E-F03-02** (P0D, cobre F03-AC02) — Uma rota privada acessada com token ausente, vencido, adulterado ou revogado. Variar os quatro estados com massa efêmera, comparar as respostas e conferir a persistência -> O acesso retorna 401 sem executar a operação. Modo: Base.
- **E2E-F03-03** (P0D, cobre F03-AC03) — Um morador com sessão válida em rota administrativa. Enviar o mesmo POST como administrador e morador, comparar estados e status -> O acesso retorna 403 sem efetivar mutação. Modo: Base.
- **E2E-F03-04** (P0D, cobre F03-AC04) — A identidade centralizada indisponível em teste isolado. Induzir falha da introspecção, obter 503 e comparar o estado após reativar o serviço -> O consumidor devolve erro de dependência e não executa a ação. Modo: Base.
- **E2E-F03-05** (P0D, cobre F03-SEC01) — Uma sessão autenticada encerrada pelo usuário. Fazer logout, retomar a rota privada e reapresentar o bearer anterior -> A sessão perde validade no servidor e o navegador retorna ao login. Modo: Base.
- **E2E-F03-06** (P0D, cobre F03-SEC02) — Login com senha errada ou conta inexistente. Comparar corpo e status dos erros e revisar o conteúdo do registro da aplicação -> A resposta recusa acesso sem confirmar a existência da conta ou revelar segredo. Modo: Base.
- **E2E-F03-07** (P0D, cobre NFR01-AC01) — Dado Um bearer QA_A foi emitido e encerrado por POST /api/auth/logout; quando reutilizar esse bearer em GET /api/auth/me -> Então HTTP 401 INVALID_SESSION e ausência de perfil no corpo. Modo: Base: HTTP real.
- **E2E-F03-08** (P0D, cobre NFR03-AC01) — Dado Um login sintético inválido e uma sessão QA_A válida; quando executar POST /api/auth/login com senha inválida e GET /api/auth/me com a sessão válida; inspecionar corpos e logs sanitizados -> Então recusa 401 não repete a senha, perfil 200 exclui password_hash e logs não contêm senha nem token. Modo: Base: HTTP real.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F03-01 | F03-AC01 | Base |
| E2E-F03-02 | F03-AC02 | Base |
| E2E-F03-03 | F03-AC03 | Base |
| E2E-F03-04 | F03-AC04 | Base |
| E2E-F03-05 | F03-SEC01 | Base |
| E2E-F03-06 | F03-SEC02 | Base |
| E2E-F03-07 | NFR01-AC01 | Base |
| E2E-F03-08 | NFR03-AC01 | Base |
