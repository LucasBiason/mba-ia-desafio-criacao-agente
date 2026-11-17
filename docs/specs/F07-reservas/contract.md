# Contrato de verificação — F07 — Reservas e agenda por área

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F07-01** (P0D, cobre F07-AC01) — Uma conta moradora vinculada e reservas em duas unidades distintas. Autenticar, selecionar a unidade e comparar a projeção com a agenda administrativa -> A consulta mostra somente reservas da unidade autorizada. Modo: Base.
- **E2E-F07-02** (P0D, cobre F07-AC02) — Duas confirmações próprias para a mesma área e data. Disparar aprovações simultâneas em duas sessões e somar projeções de ambas as unidades -> Duas aprovações retornam o contrato previsto e fica uma única reserva ativa. Modo: Aula do agente.
- **E2E-F07-03** (P0D, cobre F07-AC03) — Uma reserva ativa própria é cancelada e o mesmo slot é reservado novamente. Exercitar tool de cancelamento e de criação e comparar códigos e estado antes e depois -> Cancelamento não cria pendência e o código novo difere do anterior e dos iniciais. Modo: Aula do agente.
- **E2E-F07-04** (P0D, cobre F07-AC04) — Um administrador abre a agenda de uma área em uma data. Clicar em dias ocupados e vazios no mês, filtrar uma área e buscar um código de outra área -> O calendário mostra os horários e os titulares, e clicar em uma data abre a lista do dia. Modo: Base.
- **E2E-F07-05** (P0D, cobre F07-AC05) — Uma área gratuita e outra com taxa positiva estão disponíveis. Executar as duas intenções e comparar eventos, pendências e reservas antes e depois da aprovação -> A gratuita é gravada sem pendência e a paga fica pendente até decisão pela API. Modo: Aula do agente.
- **E2E-F07-06** (P0D, cobre F07-SEC01) — Morador consulta a agenda de unidade alheia. Consultar a API com dois vínculos distintos e comparar o corpo de recusa -> A API bloqueia acesso e o corpo não contém titular, códigos ou dados de outra unidade. Modo: Base.
- **E2E-F07-07** (P0D, cobre NFR01-AC01) — Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável -> A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. Modo: Base.
- **E2E-F07-08** (P0D, cobre NFR02-AC01) — Reinício da dependência, corrida de gravação ou falha antes de concluir a escrita. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita -> Efeito confirmado permanece. A falha é observável e o domínio fica consistente. Modo: Base.
- **E2E-F07-09** (P0D, cobre NFR03-AC01) — Operação privada bem-sucedida ou recusada. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas -> A evidência não inclui segredos ou objetos de unidades fora da autorização. Modo: Base.
- **E2E-F07-10** (P0D, cobre F07-AC06) — Uma reserva existente precisa de horário. Atualizar horários válidos, testar intervalo invertido e acesso de morador à edição, consultar a reserva pelo titular -> Administração salva início e fim em ordem e o morador titular vê os horários. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F07-01 | F07-AC01 | Base |
| E2E-F07-02 | F07-AC02 | Aula do agente |
| E2E-F07-03 | F07-AC03 | Aula do agente |
| E2E-F07-04 | F07-AC04 | Base |
| E2E-F07-05 | F07-AC05 | Aula do agente |
| E2E-F07-06 | F07-SEC01 | Base |
| E2E-F07-07 | NFR01-AC01 | Base |
| E2E-F07-08 | NFR02-AC01 | Base |
| E2E-F07-09 | NFR03-AC01 | Base |
| E2E-F07-10 | F07-AC06 | Base |

A cobertura é uma previsão. O [registro de validação](../../validacao.md) distingue provas executadas, verificações documentais e etapas ainda dependentes da prática.

## Resultado disponível

A [validação](../../validacao.md) registra execuções anteriores por superfície. O contrato conserva os critérios que ainda exigem prova. Esta atualização documental não equivale à execução de todos os itens P0D. Conferir a [matriz de entrega](../../entrega-01.md) antes de promover o estado da funcionalidade.
