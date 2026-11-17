# NFR01 — Identidade, autorização e confirmação

Applies to: F02, F03, F04, F05, F07, F08, F09, F10

## Descrição

Validar JWT, identidade, papel e escopo do recurso nas rotas privadas. Nas ações de agentes, a unidade é um dado da sessão autorizada e ações sensíveis exigem decisão explícita pela API.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| NFR01-AC01 | Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado | Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável |

## Método de medição

Execute o teste da matriz de cada funcionalidade em uma composição local isolada. Guarde os estados anterior e posterior, os códigos de resposta ou a verificação de serviço, e registre a revisão. Uma ausência de evidência permanece visível no relatório de validação.
