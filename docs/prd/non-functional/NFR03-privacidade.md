# NFR03 — Privacidade e mínimo acesso

Applies to: F02, F03, F04, F06, F07, F08, F09, F10, F11, F12, F13, F14

## Descrição

Limitar projeções ao papel e ao vínculo verificado. Usar dados sintéticos na verificação e excluir senhas, hashes, bearer e segredos de respostas e evidência publicada.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| NFR03-AC01 | QA_A lê seu perfil e recursos de 9101; tenta recurso de QA_B/9102; consulta o histórico público | Somente campos autorizados são retornados e a recusa não revela conteúdo de QA_B; histórico público não contém instruções internas nem payloads de tools | Executar NFR03-AC01 de cada feature e inspecionar corpos e registros sanitizados contra os campos permitidos e os marcadores sintéticos de QA_B |

## Método de medição

Use a composição isolada e os pré-requisitos do contrato de cada feature. Cada ramo tem uma requisição nomeada, identidade, estado anterior, resposta e estado posterior; não selecione somente o ramo favorável. Reinícios conservam volumes e não executam restore. Guarde as provas sanitizadas fora do repositório, identificadas por revisão e item P0D, e remova somente os recursos adquiridos para QA. Um lint documental não comprova runtime nem aceite humano. Backup, exportação e retenção adicional não integram este critério.
