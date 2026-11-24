# Plano de implementação — F08 — Autorizações de visita

## Dependências


## Passos de implementação

### SI08.1 — Importar autorizações e servir as projeções

- Tipo: comportamento.
- Depende de: F02 disponível.
- Ações: Importar nome, data e unidade. Expor consultas por papel e a atualização administrativa dos horários.
- Testes: Abrir as listas como administração e morador e verificar recusa de unidade alheia, salvar horários e validar a sequência de entrada e saída.
- Critérios: F08-AC04, F08-AC05, F08-SEC01.

### SI08.2 — Integrar autorização à confirmação do assistente

- Tipo: comportamento.
- Depende de: SI08.1 e etapa de confirmações de F09.
- Ações: Extrair proposta tipada, validar explicitamente operação/nome/data e contexto, vincular a ferramenta fixa ao envelope do turno e criar a pendência idempotente no ledger. Serializar o resultado canônico; gravar a autorização somente depois da aprovação persistida pela rota humana.
- Testes: Exercitar pedido completo com confirmação verbal na mesma mensagem, em sessão existente com recusas anteriores: exigir pendência e zero autorização. Verificar duplicação de tool, dados inválidos, negação, aprovação, replay 409, reinício e tentativa de consulta fora da sessão; comparar o prefixo do histórico sem apagar eventos.
- Critérios: F08-AC01, F08-AC02, F08-AC03.

### SI08.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para autorizações de visita.
- Testes: consultar GET /api/resident/visits?apartment=9102 com QA_A; confirmar que HTTP 403 APARTMENT_FORBIDDEN e nenhum nome, horário ou autorização de 9102; reiniciar visits e agent sem restore e consultar GET /api/resident/visits?apartment=9101 com QA_A; confirmar que a autorização conserva id, nome, data e horários e não aparece duplicada; consultar GET /api/resident/visits?apartment=9101 com QA_A; confirmar que a lista contém apenas a visita do titular autorizado, sem nome ou id de QA_VISIT_B e sem credenciais.
- Critérios: NFR01-AC01, NFR02-AC01, NFR03-AC01.
