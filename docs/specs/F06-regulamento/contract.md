# Contrato de verificação — F06 — Regulamento único e versionado

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F06-01** (P0D, cobre F06-AC01) — Um administrador edita a versão zero ativa. Salvar o novo texto, abrir a versão atual e comparar ambas as entradas no histórico -> A versão um fica vigente com autoria e hora, e a versão zero permanece no histórico. Modo: Base.
- **E2E-F06-02** (P0D, cobre F06-AC02) — Duas contas editam a mesma versão-base. Enviar duas edições com a mesma versão-base e conferir que foi criada uma única revisão -> A atualização desatualizada retorna conflito e preserva o conteúdo vigente. Modo: Base.
- **E2E-F06-03** (P0D, cobre F06-AC03) — Um morador autenticado tenta publicar uma edição. Consultar o texto vigente como morador, tentar PUT na rota admin e comparar versões -> O acesso de escrita é recusado sem alteração do histórico. Modo: Base.
- **E2E-F06-04** (P0D, cobre F06-AC04) — Uma revisão publicada antes de reiniciar o serviço. Publicar alteração, reiniciar o domínio e comparar o histórico com a captura anterior -> A versão e o autor permanecem consultáveis após o reinício. Modo: Base.
- **E2E-F06-05** (P0D, cobre F06-SEC01) — Uma conta moradora solicita a versão vigente ou a rota de histórico admin. Consultar ambos os caminhos e verificar o papel exigido -> A leitura vigente funciona e o histórico administrativo não é entregue ao morador. Modo: Base.
- **E2E-F06-06** (P0D, cobre NFR02-AC01) — Dado QA_ADMIN leu a versão V do regulamento vigente; quando publicar um texto sintético novo em PUT /api/admin/regulation com base_version=V; reiniciar parameters e ler vigente e /versions -> Então vigente permanece V+1 e histórico conserva V e V+1 com o texto e autor publicados. Modo: Base: HTTP real e reinício.
- **E2E-F06-07** (P0D, cobre NFR03-AC01) — Dado QA_A é resident e QA_ADMIN publicou o texto sintético; quando consultar GET /api/resident/regulation e GET /api/admin/regulation/versions usando QA_A -> Então vigente retorna 200 sem credenciais; histórico administrativo retorna 403 sem revisões de autoria alheia. Modo: Base: HTTP real.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F06-01 | F06-AC01 | Base |
| E2E-F06-02 | F06-AC02 | Base |
| E2E-F06-03 | F06-AC03 | Base |
| E2E-F06-04 | F06-AC04 | Base |
| E2E-F06-05 | F06-SEC01 | Base |
| E2E-F06-06 | NFR02-AC01 | Base |
| E2E-F06-07 | NFR03-AC01 | Base |
