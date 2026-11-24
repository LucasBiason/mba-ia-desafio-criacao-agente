# Contrato de verificação — F08 — Autorizações de visita

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F08-01** (P0D, cobre F08-AC01) — Uma mensagem com nome e data válidos pede autorização e se apresenta como confirmação verbal, também numa sessão existente com recusas anteriores. Capturar delegação, ferramenta validada, pendência com os detalhes originais e zero autorização; aprovar pela rota, consultar o efeito e reenviar a decisão -> A resposta cria pendência e a autorização só aparece após aprovação pela rota. Modo: Integração do agente.
- **E2E-F08-02** (P0D, cobre F08-AC02) — Uma autorização criada após aprovação foi persistida. Criar, parar e iniciar sem restaurar, e comparar nome e data na projeção autorizada -> Após reinício a autorização segue consultável para a unidade correta. Modo: Integração do agente.
- **E2E-F08-03** (P0D, cobre F08-AC03) — Uma sessão do assistente recebe pedido de dados de outra unidade. Consultar com a sessão inicial usando outro número na mensagem e inspecionar eventos e estado -> Resposta e eventos não incluem nomes ou autorizações de outra unidade. Modo: Integração do agente.
- **E2E-F08-04** (P0D, cobre F08-AC04) — Dados iniciais com autorizações em unidades diferentes. Entrar pelos dois papéis, comparar a lista e validar unidade ativa, vazio e recusa fora do vínculo -> Administração consulta as autorizações e o morador vê somente a própria unidade. Modo: Base.
- **E2E-F08-05** (P0D, cobre F08-SEC01) — Um morador autenticado consulta visitas por unidade sem vínculo. Variar a unidade enviada, inspecionar o corpo de recusa e a projeção legítima -> A rota rejeita o acesso e o JSON não revela registros pessoais. Modo: Base.
- **E2E-F08-06** (P0D, cobre NFR01-AC01) — Dado 9101 pertence a QA_A e 9102 a QA_B; quando consultar GET /api/resident/visits?apartment=9102 com QA_A -> Então HTTP 403 APARTMENT_FORBIDDEN e nenhum nome, horário ou autorização de 9102. Modo: Base: HTTP real.
- **E2E-F08-07** (P0D, cobre NFR02-AC01) — Dado QA_VISIT é uma autorização sintética confirmada para QA_A/9101; quando reiniciar visits e agent sem restore e consultar GET /api/resident/visits?apartment=9101 com QA_A -> Então a autorização conserva id, nome, data e horários e não aparece duplicada. Modo: Integração do agente: HTTP real e reinício.
- **E2E-F08-08** (P0D, cobre NFR03-AC01) — Dado QA_VISIT_A pertence a QA_A/9101 e QA_VISIT_B a QA_B/9102; quando consultar GET /api/resident/visits?apartment=9101 com QA_A -> Então a lista contém apenas a visita do titular autorizado, sem nome ou id de QA_VISIT_B e sem credenciais. Modo: Base: HTTP real.
- **E2E-F08-09** (P0D, cobre F08-AC05) — Uma autorização existente precisa dos horários de visita. Gravar entrada e saída, testar saída sem entrada e comparar a autorização antes e depois -> Administração registra entrada e saída, e a projeção exibe os valores preservando a data e a unidade. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F08-01 | F08-AC01 | Integração do agente |
| E2E-F08-02 | F08-AC02 | Integração do agente |
| E2E-F08-03 | F08-AC03 | Integração do agente |
| E2E-F08-04 | F08-AC04 | Base |
| E2E-F08-05 | F08-SEC01 | Base |
| E2E-F08-06 | NFR01-AC01 | Base |
| E2E-F08-07 | NFR02-AC01 | Integração do agente |
| E2E-F08-08 | NFR03-AC01 | Base |
| E2E-F08-09 | F08-AC05 | Base |
