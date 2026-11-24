# NFR02 — Durabilidade e integridade

Applies to: F01, F05, F06, F07, F08, F09

## Descrição

Conservar efeitos confirmados, eventos, pendências e histórico no armazenamento persistente. Reinício não restaura fixtures. A restrição do banco decide uma disputa por área/data.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| NFR02-AC01 | Uma escrita confirmada é consultada após reinício sem restore; duas decisões disputam a mesma área/data em F07 | Escrita e histórico persistem; disputa conserva exatamente uma reserva ativa e reenvio não duplica o efeito | Executar NFR02-AC01 específico em F01/F05/F06/F07/F08/F09, capturando IDs, versões, contagem e resposta definidos no contrato |

## Método de medição

Use a composição isolada e os pré-requisitos do contrato de cada feature. Cada ramo tem uma requisição nomeada, identidade, estado anterior, resposta e estado posterior; não selecione somente o ramo favorável. Reinícios conservam volumes e não executam restore. Guarde as provas sanitizadas fora do repositório, identificadas por revisão e item P0D, e remova somente os recursos adquiridos para QA. Um lint documental não comprova runtime nem aceite humano. Backup, exportação e retenção adicional não integram este critério.
