# Plano de implementação — F07 — Reservas e agenda por área

## Dependências


## Passos de implementação

### SI07.1 — Publicar agenda e reservas próprias

- Tipo: comportamento.
- Depende de: F02 e F05 disponíveis.
- Ações: Importar o histórico, implementar projeções por papel e filtros e ligar o calendário por área, a busca por código, o registro de horários e a consulta do morador.
- Testes: Comparar APIs e navegação, dias ocupados e busca por código. Exercitar atualização de horários e escopo por papel.
- Critérios: F07-AC01, F07-AC04, F07-AC06, F07-SEC01.

### SI07.2 — Conectar as operações de reserva na integração

- Tipo: comportamento.
- Depende de: SI07.1 e etapas de consulta e confirmação de F09.
- Ações: Acoplar ferramentas tipadas, validar identidade de sessão, aplicar exclusividade transacional e preservar códigos históricos.
- Testes: Provar fluxo gratuito, taxa com pendência, cancelamento próprio e confirmação concorrente.
- Critérios: F07-AC02, F07-AC03, F07-AC05.

### SI07.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para reservas e agenda por área.
- Testes: consultar GET /api/resident/reservations?apartment=9102 com QA_A; confirmar que HTTP 403 APARTMENT_FORBIDDEN, sem reservas, códigos ou titular de 9102; gerar duas pendências pelo protocolo delegar_solicitacao com operation=reserve e executar_reserva_validada e aprová-las simultaneamente; consultar a agenda e repetir a decisão vencedora; confirmar que existe exatamente uma reserva ativa para área/data, a outra execução informa indisponibilidade e reenvio sequencial retorna 409 sem segundo efeito; consultar GET /api/resident/reservations?apartment=9101 com QA_A e inspecionar o corpo; confirmar que apenas QA_RES_A é retornada; não há QA_RES_B, resident_id alheio, bearer nem segredo.
- Critérios: NFR01-AC01, NFR02-AC01, NFR03-AC01.
