# F07 — Reservas e agenda por área

Domínio: Reservas | Onda: 5 | Prioridade: 1

Requisitos não funcionais relacionados: NFR01, NFR02, NFR03

## Descrição

Nesta entrega administrativa, o escopo é consulta da agenda e das reservas e edição dos horários. Criação, cobrança, confirmação e cancelamento pelo agente são a etapa posterior.

Consultar reservas em um calendário por área, localizar pelo código e registrar horários. Criar e cancelar reservas no fluxo de integração.

Como morador, quero consultar reservas da unidade selecionada e depois aprender a solicitar reservas e cancelamentos pelo assistente.

A referência de produto original é FR07. A correspondência dos critérios anteriores é F07-AC01 ↔ FR07/AC01, F07-AC02 ↔ FR07/AC02, F07-AC03 ↔ FR07/AC03, F07-AC04 ↔ FR07/AC04. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Depende de: F02, F05.
- Fornece: Projeção de agenda consumida pela interface e contrato de operações futuras com identidade e efeito controlados.
- Integração: O painel chama a API autenticada e usa filtros por área, data e estado. A interface do morador envia somente a unidade selecionada. A API verifica vínculo em cada leitura. O agente e as futuras tools recebem o contexto autenticado do servidor e executam regras do domínio antes de gravar.

## Comportamento esperado

- **Dado** uma conta moradora vinculada e reservas em duas unidades distintas
- **Quando** autenticar, selecionar a unidade e comparar a projeção com a agenda administrativa
- **Então** a consulta mostra somente reservas da unidade autorizada.

- **Dado** duas confirmações próprias para a mesma área e data
- **Quando** disparar aprovações simultâneas em duas sessões e somar projeções de ambas as unidades
- **Então** duas aprovações retornam o contrato previsto e fica uma única reserva ativa.

- **Dado** uma reserva ativa própria é cancelada e o mesmo slot é reservado novamente
- **Quando** exercitar tool de cancelamento e de criação e comparar códigos e estado antes e depois
- **Então** cancelamento não cria pendência e o código novo difere do anterior e dos iniciais.

- **Dado** um administrador abre a agenda de uma área em uma data
- **Quando** clicar em dias ocupados e vazios no mês, filtrar uma área e buscar um código de outra área
- **Então** o calendário mostra os horários e os titulares, e clicar em uma data abre a lista do dia.

- **Dado** uma área gratuita e outra com taxa positiva estão disponíveis
- **Quando** executar as duas intenções e comparar eventos, pendências e reservas antes e depois da aprovação
- **Então** a gratuita é gravada sem pendência e a paga fica pendente até decisão pela API.

- **Dado** uma reserva existente precisa de horário
- **Quando** atualizar horários válidos, testar intervalo invertido e acesso de morador à edição, consultar a reserva pelo titular
- **Então** administração salva início e fim em ordem e o morador titular vê os horários.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F07-AC01 | Uma conta moradora vinculada e reservas em duas unidades distintas | A consulta mostra somente reservas da unidade autorizada | Autenticar, selecionar a unidade e comparar a projeção com a agenda administrativa |
| F07-AC02 | Duas confirmações próprias para a mesma área e data | Duas aprovações retornam o contrato previsto e fica uma única reserva ativa | Disparar aprovações simultâneas em duas sessões e somar projeções de ambas as unidades |
| F07-AC03 | Uma reserva ativa própria é cancelada e o mesmo slot é reservado novamente | Cancelamento não cria pendência e o código novo difere do anterior e dos iniciais | Exercitar tool de cancelamento e de criação e comparar códigos e estado antes e depois |
| F07-AC04 | Um administrador abre a agenda de uma área em uma data | O calendário mostra os horários e os titulares, e clicar em uma data abre a lista do dia | Clicar em dias ocupados e vazios no mês, filtrar uma área e buscar um código de outra área |
| F07-AC05 | Uma área gratuita e outra com taxa positiva estão disponíveis | A gratuita é gravada sem pendência e a paga fica pendente até decisão pela API | Executar as duas intenções e comparar eventos, pendências e reservas antes e depois da aprovação |
| F07-AC06 | Uma reserva existente precisa de horário | Administração salva início e fim em ordem e o morador titular vê os horários | Atualizar horários válidos, testar intervalo invertido e acesso de morador à edição, consultar a reserva pelo titular |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F07-reservas/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F07-SEC01 | Fronteiras e escopo | A API bloqueia acesso e o corpo não contém titular, códigos ou dados de outra unidade | Consultar a API com dois vínculos distintos e comparar o corpo de recusa |

## Fora do escopo

Criação e cancelamento administrativos, divisão da data em vários intervalos de reserva e pagamento real. Criar e cancelar pelo chat fazem parte da integração.

## Tratamento de erros

A API recusa unidade fora do vínculo sem expor dados. A futura disputa devolve indisponibilidade sem identificar o vencedor. Falha de persistência não confirma efeito.
