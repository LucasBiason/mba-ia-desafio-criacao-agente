# Contrato de verificação — F05 — Cadastro de áreas comuns

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F05-01** (P0D, cobre F05-AC01) — Um administrador cria área com taxa zero. Cadastrar a área, abrir o catálogo do morador e comparar `fee_cents` com a indicação visual -> A área aparece no catálogo como gratuita. Modo: Base.
- **E2E-F05-02** (P0D, cobre F05-AC02) — Uma taxa negativa no cadastro ou na edição. Enviar valores inválidos e consultar a área no catálogo depois -> A requisição é rejeitada e a taxa existente permanece. Modo: Base.
- **E2E-F05-03** (P0D, cobre F05-AC03) — Um morador tenta editar uma taxa. Autenticar como morador, tentar PATCH na rota administrativa e consultar o catálogo -> A operação é recusada e a resposta seguinte preserva o valor. Modo: Base.
- **E2E-F05-04** (P0D, cobre F05-AC04) — Uma área referenciada e uma área recém-criada sem uso. Executar as duas exclusões, comparar catálogo e consultar agenda da área referenciada -> A primeira exclusão é recusada e a segunda remove o cadastro independente. Modo: Base.
- **E2E-F05-05** (P0D, cobre F05-SEC01) — Um cliente sem sessão válida tenta ler ou administrar o catálogo. Consultar as rotas de catálogo e administração sem bearer -> A API recusa o acesso autenticado sem revelar detalhes internos. Modo: Base.
- **E2E-F05-06** (P0D, cobre NFR01-AC01) — Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável -> A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. Modo: Base.
- **E2E-F05-07** (P0D, cobre NFR02-AC01) — Reinício da dependência, corrida de gravação ou falha antes de concluir a escrita. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita -> Efeito confirmado permanece. A falha é observável e o domínio fica consistente. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F05-01 | F05-AC01 | Base |
| E2E-F05-02 | F05-AC02 | Base |
| E2E-F05-03 | F05-AC03 | Base |
| E2E-F05-04 | F05-AC04 | Base |
| E2E-F05-05 | F05-SEC01 | Base |
| E2E-F05-06 | NFR01-AC01 | Base |
| E2E-F05-07 | NFR02-AC01 | Base |

A cobertura é uma previsão. O [registro de validação](../../validacao.md) distingue provas executadas, verificações documentais e etapas ainda dependentes da prática.

## Resultado disponível

A [validação](../../validacao.md) registra execuções anteriores por superfície. O contrato conserva os critérios que ainda exigem prova. Esta atualização documental não equivale à execução de todos os itens P0D. Conferir a [matriz de entrega](../../entrega-01.md) antes de promover o estado da funcionalidade.
