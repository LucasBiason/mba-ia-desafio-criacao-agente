# NFR02 — Durabilidade e integridade

Applies to: F01, F05, F06, F07, F08, F09

## Descrição

Conservar os efeitos confirmados ao reiniciar e preservar históricos. Escritas concorrentes ou falhas não devem produzir duplicidade ou estado parcialmente aplicado.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| NFR02-AC01 | Reinício da dependência, corrida de gravação ou falha antes de concluir a escrita | Efeito confirmado permanece. A falha é observável e o domínio fica consistente | Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita |

## Método de medição

Execute o teste da matriz de cada funcionalidade em uma composição local isolada. Guarde os estados anterior e posterior, os códigos de resposta ou a verificação de serviço, e registre a revisão. Uma ausência de evidência permanece visível no relatório de validação.
