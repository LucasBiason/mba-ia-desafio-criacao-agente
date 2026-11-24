# NFR04 — Operação reproduzível

Applies to: F01, F10

## Descrição

O cluster é reproduzível por configs/compose.yaml, resolução Python fixada e configuração privada local. Bootstrap e restauração são comandos explícitos; HTTP não cria tabelas.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| NFR04-AC01 | Um projeto QA novo executa a preparação e a partida documentadas; a API acadêmica usa duas réplicas e banco próprio | Preparadores concluem com exit 0 e as superfícies documentadas respondem; a sessão persiste após reinício sem restore | Executar os cenários NFR04-AC01 distintos de F01 e F10 e registrar jobs, status, bind local, sessão e eventos |

## Método de medição

Use a composição isolada e os pré-requisitos do contrato de cada feature. Cada ramo tem uma requisição nomeada, identidade, estado anterior, resposta e estado posterior; não selecione somente o ramo favorável. Reinícios conservam volumes e não executam restore. Guarde as provas sanitizadas fora do repositório, identificadas por revisão e item P0D, e remova somente os recursos adquiridos para QA. Um lint documental não comprova runtime nem aceite humano. Backup, exportação e retenção adicional não integram este critério.
