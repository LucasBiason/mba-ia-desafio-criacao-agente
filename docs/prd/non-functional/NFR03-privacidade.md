# NFR03 — Privacidade e mínimo acesso

Applies to: F02, F03, F04, F06, F07, F08, F09, F10

## Descrição

Limitar campos ao necessário por papel e unidade. Razões de recusa e registros de teste usam dados fictícios e referências reduzidas. Credenciais e tokens não entram em logs publicados.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| NFR03-AC01 | Operação privada bem-sucedida ou recusada | A evidência não inclui segredos ou objetos de unidades fora da autorização | Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas |

## Método de medição

Execute o teste da matriz de cada funcionalidade em uma composição local isolada. Guarde os estados anterior e posterior, os códigos de resposta ou a verificação de serviço, e registre a revisão. Uma ausência de evidência permanece visível no relatório de validação.
