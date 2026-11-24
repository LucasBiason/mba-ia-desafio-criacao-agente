# NFR01 — Identidade, autorização e confirmação

Applies to: F02, F03, F04, F05, F07, F08, F09, F10, F11, F12, F13, F14

## Descrição

Validar JWT, sessão revogável, papel e vínculo nas rotas privadas; a unidade de uma ação vem da sessão autorizada. Na API local acadêmica, a unidade é fixada na abertura e a decisão sensível vem da rota de confirmação.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| NFR01-AC01 | Uma sessão revogada chama /api/auth/me; um resident chama /api/admin/users; QA_A consulta recursos de 9102; uma ação paga recebe apenas sim no chat | Cada ramo é recusado na sua fronteira: 401, 403, recusa de recurso sem dados ou pendência sem efeito, respectivamente | Executar os ramos concretos NFR01-AC01 da spec de cada feature, com os handles e endpoints de seu contrato; comparar status e estado antes/depois |

## Método de medição

Use a composição isolada e os pré-requisitos do contrato de cada feature. Cada ramo tem uma requisição nomeada, identidade, estado anterior, resposta e estado posterior; não selecione somente o ramo favorável. Reinícios conservam volumes e não executam restore. Guarde as provas sanitizadas fora do repositório, identificadas por revisão e item P0D, e remova somente os recursos adquiridos para QA. Um lint documental não comprova runtime nem aceite humano. Backup, exportação e retenção adicional não integram este critério.
