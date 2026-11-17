# Aprender o agente de reservas passo a passo

A base de estudo já tem os cadastros e as consultas que a conversa vai usar. Este roteiro organiza o trabalho de orquestração em decisões pequenas. Faça uma etapa por vez e registre a chamada, o resultado esperado, o resultado observado e a dúvida antes de avançar. O [contrato do chat](specs/F09-chat-agente/contract.md) e o [contrato acadêmico](specs/F10-avaliacao/contract.md) descrevem a aceitação final.

## Preparar a primeira sessão

1. Suba a base conforme o [README](../README.md).
2. Entre como morador e selecione um apartamento autorizado. Confirme a lista de reservas existente e a abertura de sessão no chat.
3. Observe a indisponibilidade ao enviar mensagem. Essa resposta é o ponto de partida para ligar a primeira tool. Nenhuma reserva nova deve aparecer.
4. Escolha os papéis do primeiro agente e do primeiro especialista. Um desenho inicial é principal para roteamento, especialista de reservas e especialista de convivência. A pessoa em aprendizagem decide a forma de acionamento e registra a justificativa.

## 1. Primeira consulta por ferramenta

**Objetivo.** Ver um agente escolher uma tool que lê as reservas da sessão.

- Derive o apartamento no servidor a partir da sessão. A ferramenta recebe esse contexto verificado e consulta as reservas do titular para aquela unidade. Neste escopo um único usuário do tipo Morador representa o proprietário e responsável pelo apartamento. Outros ocupantes ficam fora do cadastro. O identificador interno da unidade e o identificador do morador representam entidades distintas.
- Comece pela pergunta sobre as reservas atuais. Observe separadamente a decisão de roteamento, os argumentos tipados da ferramenta e a resposta do domínio.
- Repita em contexto com dados diferentes e confira que o agente usa o resultado da ferramenta para responder.

**Prova da etapa.** O evento mostra a chamada da ferramenta e o domínio devolve a projeção da unidade da sessão.

## 2. Delimitar o contexto e adicionar especialista

**Objetivo.** Manter identidade estável enquanto o assistente alterna especialidades.

- Escolha como os especialistas são acionados e registre a versão do SDK e a configuração usadas na experiência.
- Abra sessão em uma unidade. Envie um pedido sobre outro apartamento e compare ferramenta, resultado e eventos. O escopo permanece na sessão.
- Faça a segunda especialidade buscar apenas o trecho do regulamento pertinente à pergunta. Compare o trecho da revisão vigente com a resposta e os eventos.

**Prova da etapa.** As duas especialidades executam uma trilha observável. Eventos e respostas permanecem no escopo autorizado e incluem só o conteúdo pertinente do regulamento. [F09](specs/F09-chat-agente/spec.md)

## 3. Executar reserva gratuita e cancelamento próprio

**Objetivo.** Fazer o domínio decidir e registrar o efeito.

- Antes de gravar, a ferramenta busca a área e o valor do catálogo. A regra de gratuidade é decidida em código.
- Reserve uma data livre da área gratuita, consulte a projeção e cancele uma reserva própria.
- Tente cancelar uma reserva alheia. Compare as projeções antes e depois.
- Grave outra reserva depois de cancelar e verifique que o código novo é distinto, mesmo quando a data e a área são reaproveitadas.

**Prova da etapa.** As operações próprias produzem efeitos e preservam os códigos históricos. O acesso alheio fica sem efeito e sem dados expostos. [F07](specs/F07-reservas/spec.md)

## 4. Suspender e retomar confirmação

**Objetivo.** Compreender como uma decisão da API retoma a ação original.

- Gere uma pendência para área paga com conteúdo tipado e registre a unidade da sessão. Diferencie texto do usuário, decisão na rota e efeito gravado.
- Negue uma pendência e constate que a agenda não mudou. Gere uma nova, aprove e compare a agenda.
- Reenvie a aprovação e verifique 409 sem efeito duplicado. Envie resposta para pendência inexistente e de outra sessão.
- Repita para autorização de visitante, incluindo mensagem que afirma que já houve confirmação.
- Registre qual agente ou invocação recebe a retomada e como os eventos se vinculam à ação. Confirme que a estratégia funciona com a sessão persistida.

**Prova da etapa.** Informações da ação correspondem à pendência. A decisão válida é consumida uma vez. Cancelamento e negativa preservam estado conforme a operação. [F08](specs/F08-visitantes/spec.md) · [F09](specs/F09-chat-agente/spec.md)

## 5. Testar reinício e concorrência

**Objetivo.** Tirar as regras críticas da memória do processo.

- Registre o número de eventos e uma pendência aberta. Pare o serviço e suba novamente usando as mesmas bases, sem restaurar.
- Confirme a pendência retomada, verifique a progressão de eventos e confira a agenda e as visitas.
- Abra duas sessões de unidades autorizadas para o mesmo slot pago. Dispare ambas as aprovações juntas.
- Compare os dois resultados HTTP e conte reservas ativas nas duas projeções. Verifique que o erro de indisponibilidade não identifica outro morador.

**Prova da etapa.** A sessão, as decisões e os efeitos sobrevivem ao reinício. A exclusividade é definida na gravação e fica uma única reserva ativa.

## 6. Conectar o modo acadêmico

Prepare um ambiente separado com o protocolo documentado em F10. Verifique a versão exata do ADK na configuração do projeto e mantenha a credencial do provedor apenas no ambiente local autorizado. Registre o comando de restauração e execute os 15 passos do enunciado quando as etapas anteriores tiverem evidência. O produto continua autenticado e a entrada acadêmica usa localhost:8000 em execução isolada. [F10](specs/F10-avaliacao/spec.md)

## Primeira implementação acompanhada

Comece pela **Etapa 1**. A pergunta a responder é como transformar uma mensagem em uma consulta real, carregando a identidade da sessão até a ferramenta. Depois confira os eventos da primeira consulta antes de escolher o fluxo de confirmação.
