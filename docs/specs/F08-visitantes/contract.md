# Contrato de verificação — F08 — Autorizações de visita

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F08-01** (P0D, cobre F08-AC01) — Uma mensagem pede autorização e se apresenta como confirmação verbal. Capturar eventos e consultar antes e depois de responder a pendência pela API -> A resposta cria pendência e a autorização só aparece após aprovação pela rota. Modo: Aula do agente.
- **E2E-F08-02** (P0D, cobre F08-AC02) — Uma autorização criada após aprovação foi persistida. Criar, parar e iniciar sem restaurar, e comparar nome e data na projeção autorizada -> Após reinício a autorização segue consultável para a unidade correta. Modo: Aula do agente.
- **E2E-F08-03** (P0D, cobre F08-AC03) — Uma sessão do assistente recebe pedido de dados de outra unidade. Consultar com a sessão inicial usando outro número na mensagem e inspecionar eventos e estado -> Resposta e eventos não incluem nomes ou autorizações de outra unidade. Modo: Aula do agente.
- **E2E-F08-04** (P0D, cobre F08-AC04) — Dados iniciais com autorizações em unidades diferentes. Entrar pelos dois papéis, comparar a lista e validar unidade ativa, vazio e recusa fora do vínculo -> Administração consulta as autorizações e o morador vê somente a própria unidade. Modo: Base.
- **E2E-F08-05** (P0D, cobre F08-SEC01) — Um morador autenticado consulta visitas por unidade sem vínculo. Variar a unidade enviada, inspecionar o corpo de recusa e a projeção legítima -> A rota rejeita o acesso e o JSON não revela registros pessoais. Modo: Base.
- **E2E-F08-06** (P0D, cobre NFR01-AC01) — Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável -> A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. Modo: Base.
- **E2E-F08-07** (P0D, cobre NFR02-AC01) — Reinício da dependência, corrida de gravação ou falha antes de concluir a escrita. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita -> Efeito confirmado permanece. A falha é observável e o domínio fica consistente. Modo: Base.
- **E2E-F08-08** (P0D, cobre NFR03-AC01) — Operação privada bem-sucedida ou recusada. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas -> A evidência não inclui segredos ou objetos de unidades fora da autorização. Modo: Base.
- **E2E-F08-09** (P0D, cobre F08-AC05) — Uma autorização existente precisa dos horários de visita. Gravar entrada e saída, testar saída sem entrada e comparar a autorização antes e depois -> Administração registra entrada e saída, e a projeção exibe os valores preservando a data e a unidade. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F08-01 | F08-AC01 | Aula do agente |
| E2E-F08-02 | F08-AC02 | Aula do agente |
| E2E-F08-03 | F08-AC03 | Aula do agente |
| E2E-F08-04 | F08-AC04 | Base |
| E2E-F08-05 | F08-SEC01 | Base |
| E2E-F08-06 | NFR01-AC01 | Base |
| E2E-F08-07 | NFR02-AC01 | Base |
| E2E-F08-08 | NFR03-AC01 | Base |
| E2E-F08-09 | F08-AC05 | Base |

A cobertura é uma previsão. O [registro de validação](../../validacao.md) distingue provas executadas, verificações documentais e etapas ainda dependentes da prática.

## Resultado disponível

A [validação](../../validacao.md) registra execuções anteriores por superfície. O contrato conserva os critérios que ainda exigem prova. Esta atualização documental não equivale à execução de todos os itens P0D. Conferir a [matriz de entrega](../../entrega-01.md) antes de promover o estado da funcionalidade.
