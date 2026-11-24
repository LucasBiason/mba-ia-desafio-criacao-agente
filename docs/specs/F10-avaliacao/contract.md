# Contrato de verificação — F10 — Compatibilidade e aceite do desafio

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F10-01** (P0D, cobre F10-AC01) — Um clone limpo com dependências e chave própria autorizada. Seguir o roteiro de partida, restaurar os dados, registrar códigos e observar estado e eventos em cada passo -> O avaliador executa os 15 passos na porta 8000 com o protocolo completo. Modo: Avaliação do desafio.
- **E2E-F10-02** (P0D, cobre F10-AC02) — A composição base do produto é consultada pelo proxy publicado. Consultar rotas locais planejadas na origem do produto e tentar APIs privadas sem bearer -> Caminhos do assistente e rotas internas não contornam a autenticação. Modo: Base.
- **E2E-F10-03** (P0D, cobre F10-AC03) — O fork está em preparação final após a aula. Comparar hashes dos dados, revisar o lock e verificar os links das garantias -> Cinco fixtures correspondem à origem e o README identifica provas e trechos implementados. Modo: Avaliação do desafio.
- **E2E-F10-04** (P0D, cobre F10-AC04) — A base é construída e iniciada com seu comando de demonstração. Conferir os hashes das fixtures antes da partida e depois do teste com volumes isolados -> As cinco fixtures mantêm o mesmo conteúdo entre a cópia e o ambiente inicializado. Modo: Base.
- **E2E-F10-05** (P0D, cobre F10-SEC01) — O modo avaliador é iniciado numa composição descartável. Conferir bind, isolamento de armazenamento, rota de autenticação do produto e diff de configuração -> O exercício roda localmente, com dados separados e sem publicar segredos. Modo: Avaliação do desafio.
- **E2E-F10-06** (P0D, cobre NFR01-AC01) — Dado Uma sessão acadêmica fixa apartamento 101 e possui reserva paga pendente QA_PENDING; quando enviar texto sim em /sessoes/{QA_SESSION}/mensagens sem chamar /confirmacoes e consultar /apartamentos/101/reservas -> Então a ação permanece pendente e nenhuma reserva paga nova existe; somente decisão externa válida poderá liberá-la. Modo: Avaliação do desafio: Gemini e HTTP reais.
- **E2E-F10-07** (P0D, cobre NFR03-AC01) — Dado QA_SESSION fixa apartamento 101 e outra sessão usa 202; quando pedir nomes de visitantes de 202 pela sessão 101 e inspecionar resposta, eventos e projeção de 101 -> Então tools mantêm apartamento 101 e a resposta não revela nome de 202 ou segredos; eventos de execução não contêm credenciais. Modo: Avaliação do desafio: Gemini e HTTP reais.
- **E2E-F10-08** (P0D, cobre NFR04-AC01) — Dado Uma composição isolada tem agent-a e agent-b sobre o mesmo agent-db; quando criar QA_SESSION via POST /sessoes, enviar consulta e ler eventos via gateway; reiniciar uma réplica sem restore e reler eventos -> Então as seis rotas estão disponíveis em 8000 e a mesma sessão/eventos persistem entre réplicas, sem estado do portal. Modo: Avaliação do desafio: PostgreSQL, Gemini e HTTP reais.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F10-01 | F10-AC01 | Avaliação do desafio |
| E2E-F10-02 | F10-AC02 | Base |
| E2E-F10-03 | F10-AC03 | Avaliação do desafio |
| E2E-F10-04 | F10-AC04 | Base |
| E2E-F10-05 | F10-SEC01 | Avaliação do desafio |
| E2E-F10-06 | NFR01-AC01 | Avaliação do desafio |
| E2E-F10-07 | NFR03-AC01 | Avaliação do desafio |
| E2E-F10-08 | NFR04-AC01 | Avaliação do desafio |
