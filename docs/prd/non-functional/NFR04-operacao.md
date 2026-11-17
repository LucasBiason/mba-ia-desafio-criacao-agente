# NFR04 — Operação reproduzível

Applies to: F01, F10

## Descrição

A base de produto é reproduzível via Compose. O avaliador, quando implementado, tem partida e restauração separadas em ambiente local, com lock e arquivo de configuração de exemplo.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| NFR04-AC01 | Execução da base ou execução isolada do protocolo acadêmico | As dependências do modo escolhido atingem prontidão e os verificadores registram a condição observada | Executar o procedimento aplicável a partir de uma instalação isolada e registrar componentes, saídas e condições não exercitadas |

## Método de medição

Execute o teste da matriz de cada funcionalidade em uma composição local isolada. Guarde os estados anterior e posterior, os códigos de resposta ou a verificação de serviço, e registre a revisão. Uma ausência de evidência permanece visível no relatório de validação.
