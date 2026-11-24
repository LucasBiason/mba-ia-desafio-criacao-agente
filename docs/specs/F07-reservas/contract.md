# Contrato de verificação — F07 — Reservas e agenda por área

## Pré-requisitos

Use um projeto Compose exclusivo de QA e volumes novos, sem publicar sobre 8770/8000 já ocupados. Registre revisão e nomes dos recursos adquiridos; credenciais ficam somente no ambiente privado do executor. Nunca use o cluster pessoal nem altere os cinco arquivos de `dados/`. O bootstrap explícito deve terminar antes de HTTP.

Handles do cenário: `QA_ADMIN` é a conta administrativa de demonstração autenticada; por POST `/api/admin/users`, crie `QA_A` e `QA_B` como residents ativos com emails sintéticos distintos e retenha os IDs e bearers somente em memória. Por POST `/api/admin/apartments`, crie `9101`→QA_A e `9102`→QA_B; `QA_AREA` é a área `qa-area` criada em POST `/api/admin/areas` com taxa 100. Capture IDs retornados em vez de supor IDs internos. `QA_DAY` é uma data futura livre escolhida após consulta da agenda. `QA_RES_A`, `QA_RES_B` e `QA_VISIT` são códigos/IDs retornados pelas ações confirmadas na integração quando o cenário os utiliza; nomes de visitantes são sintéticos. `QA_SESSION_A` e `QA_PENDING` são IDs retornados pela abertura de sessão e pela pendência original. Cenários acadêmicos usam separadamente `QA_SESSION` retornado por POST `/sessoes` com apartamento 101; não reutilizam JWT ou dados do portal.

A massa de cada item é preparada novamente em volume descartável para não depender do item anterior. Para casos de navegador use contextos separados para QA_ADMIN, QA_A e QA_B; desktop 1280×900 e celular 390×844. Ao terminar ou falhar, feche os contextos e remova exclusivamente contêineres, rede e volumes do projeto QA registrado, sem executar restore no ambiente pessoal. Provas externas guardam status, campos permitidos, contagens e hashes; não publicam senha ou bearer. A preparação descreve o ensaio e não concede execução ou aceite humano.

## Itens

- **E2E-F07-01** (P0D, cobre F07-AC01) — Uma conta moradora vinculada e reservas em duas unidades distintas. Autenticar, selecionar a unidade e comparar a projeção com a agenda administrativa -> A consulta mostra somente reservas da unidade autorizada. Modo: Base.
- **E2E-F07-02** (P0D, cobre F07-AC02) — Duas confirmações próprias para a mesma área e data. Disparar aprovações simultâneas em duas sessões e somar projeções de ambas as unidades -> Duas aprovações retornam o contrato previsto e fica uma única reserva ativa. Modo: Integração do agente.
- **E2E-F07-03** (P0D, cobre F07-AC03) — Uma reserva ativa própria é cancelada e o mesmo slot é reservado novamente. Exercitar tool de cancelamento e de criação e comparar códigos e estado antes e depois -> Cancelamento não cria pendência e o código novo difere do anterior e dos iniciais. Modo: Integração do agente.
- **E2E-F07-04** (P0D, cobre F07-AC04) — Um administrador abre a agenda de uma área em uma data. Clicar em dias ocupados e vazios no mês, filtrar uma área e buscar um código de outra área -> O calendário mostra os horários e os titulares, e clicar em uma data abre a lista do dia. Modo: Base.
- **E2E-F07-05** (P0D, cobre F07-AC05) — Uma área gratuita e outra com taxa positiva estão disponíveis. Executar as duas intenções e comparar eventos, pendências e reservas antes e depois da aprovação -> A gratuita é gravada sem pendência e a paga fica pendente até decisão pela API. Modo: Integração do agente.
- **E2E-F07-06** (P0D, cobre F07-SEC01) — Morador consulta a agenda de unidade alheia. Consultar a API com dois vínculos distintos e comparar o corpo de recusa -> A API bloqueia acesso e o corpo não contém titular, códigos ou dados de outra unidade. Modo: Base.
- **E2E-F07-07** (P0D, cobre NFR01-AC01) — Dado 9101 pertence a QA_A e 9102 a QA_B; quando consultar GET /api/resident/reservations?apartment=9102 com QA_A -> Então HTTP 403 APARTMENT_FORBIDDEN, sem reservas, códigos ou titular de 9102. Modo: Base: HTTP real.
- **E2E-F07-08** (P0D, cobre NFR02-AC01) — Dado Duas sessões autorizadas disputam a mesma QA_AREA paga na data QA_DAY livre; quando gerar duas pendências pelo protocolo delegar_solicitacao com operation=reserve e executar_reserva_validada e aprová-las simultaneamente; consultar a agenda e repetir a decisão vencedora -> Então existe exatamente uma reserva ativa para área/data, a outra execução informa indisponibilidade e reenvio sequencial retorna 409 sem segundo efeito. Modo: Integração do agente: HTTP e banco reais.
- **E2E-F07-09** (P0D, cobre NFR03-AC01) — Dado Há uma reserva QA_RES_A de QA_A/9101 e QA_RES_B de QA_B/9102; quando consultar GET /api/resident/reservations?apartment=9101 com QA_A e inspecionar o corpo -> Então apenas QA_RES_A é retornada; não há QA_RES_B, resident_id alheio, bearer nem segredo. Modo: Base: HTTP real.
- **E2E-F07-10** (P0D, cobre F07-AC06) — Uma reserva existente precisa de horário. Atualizar horários válidos, testar intervalo invertido e acesso de morador à edição, consultar a reserva pelo titular -> Administração salva início e fim em ordem e o morador titular vê os horários. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F07-01 | F07-AC01 | Base |
| E2E-F07-02 | F07-AC02 | Integração do agente |
| E2E-F07-03 | F07-AC03 | Integração do agente |
| E2E-F07-04 | F07-AC04 | Base |
| E2E-F07-05 | F07-AC05 | Integração do agente |
| E2E-F07-06 | F07-SEC01 | Base |
| E2E-F07-07 | NFR01-AC01 | Base |
| E2E-F07-08 | NFR02-AC01 | Integração do agente |
| E2E-F07-09 | NFR03-AC01 | Base |
| E2E-F07-10 | F07-AC06 | Base |
