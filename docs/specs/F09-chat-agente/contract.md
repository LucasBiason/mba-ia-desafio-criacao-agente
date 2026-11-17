# Contrato de verificação — F09 — Chat do morador e agente

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F09-01** (P0D, cobre F09-AC01) — Uma conta moradora tem duas unidades, abre sessão em uma e solicita mudança por mensagem. Registrar identidade entregue à tool e comparar resposta, eventos e projeções diante do pedido de troca -> As tools continuam no escopo da unidade escolhida na abertura. Modo: Integração do agente.
- **E2E-F09-02** (P0D, cobre F09-AC02) — Uma conta administrativa tenta abrir chat em nome de um morador. Enviar POST de abertura com JWT administrativo e comparar as sessões existentes -> O serviço recusa a sessão e não faz ação em nome de outra conta. Modo: Base.
- **E2E-F09-03** (P0D, cobre F09-AC03) — Uma reserva paga aguarda confirmação antes de reiniciar o processo. Criar pendência, reiniciar sem restaurar, aprovar e comparar agenda e reenvio -> Após reinício a decisão válida produz um efeito e o reenvio sequencial retorna 409. Modo: Integração do agente.
- **E2E-F09-04** (P0D, cobre F09-AC04) — O morador pergunta pelo horário de fechamento da piscina aos domingos. Comparar a versão do regulamento, resposta, tool chamada e texto persistido em eventos -> A resposta usa o horário vigente e os eventos não contêm assuntos não consultados. Modo: Integração do agente.
- **E2E-F09-05** (P0D, cobre F09-AC05) — Um morador abre uma sessão numa unidade autorizada e envia uma mensagem. Abrir sessão, recarregar o navegador, consultar o detalhe e enviar texto com o agente desativado -> Após reabrir a tela a unidade continua fixa e a mensagem recebe indisponibilidade identificável. Modo: Base.
- **E2E-F09-06** (P0D, cobre F09-SEC01) — Dois moradores têm sessões distintas ou uma conta perde o vínculo anterior. Criar sessões de contas distintas e testar consulta e mensagem com o bearer de outra conta -> Uma sessão alheia não é legível nem utilizável e o vínculo vigente é checado nas ações privadas. Modo: Base.
- **E2E-F09-07** (P0D, cobre NFR01-AC01) — Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável -> A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. Modo: Base.
- **E2E-F09-08** (P0D, cobre NFR02-AC01) — Reinício da dependência, corrida de gravação ou falha antes de concluir a escrita. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita -> Efeito confirmado permanece. A falha é observável e o domínio fica consistente. Modo: Base.
- **E2E-F09-09** (P0D, cobre NFR03-AC01) — Operação privada bem-sucedida ou recusada. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas -> A evidência não inclui segredos ou objetos de unidades fora da autorização. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F09-01 | F09-AC01 | Integração do agente |
| E2E-F09-02 | F09-AC02 | Base |
| E2E-F09-03 | F09-AC03 | Integração do agente |
| E2E-F09-04 | F09-AC04 | Integração do agente |
| E2E-F09-05 | F09-AC05 | Base |
| E2E-F09-06 | F09-SEC01 | Base |
| E2E-F09-07 | NFR01-AC01 | Base |
| E2E-F09-08 | NFR02-AC01 | Base |
| E2E-F09-09 | NFR03-AC01 | Base |
