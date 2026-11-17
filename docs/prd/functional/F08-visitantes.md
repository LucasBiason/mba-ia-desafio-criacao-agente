# F08 — Autorizações de visita

Domínio: Acesso ao residencial | Onda: 5 | Prioridade: 1

Conforms to: NFR01, NFR02, NFR03

## Situação na primeira entrega

**Parcial.** O recorte implementado é consulta por papel e registro de entrada e saída. Código de referência em `services/domain/app.py` e `web/src/records.jsx`. Evidência disponível em [validação](../../validacao.md) e [pacote de entrega](../../entrega-01.md). A tabela abaixo registra o alcance de cada critério.

| Critério | Situação documental |
| --- | --- |
| F08-AC01 | Pendente — agente ou avaliação acadêmica |
| F08-AC02 | Pendente — agente ou avaliação acadêmica |
| F08-AC03 | Pendente — agente ou avaliação acadêmica |
| F08-AC04 | Implementação presente; evidência e aceite vinculados ao contrato |
| F08-AC05 | Implementação presente; evidência e aceite vinculados ao contrato |
| F08-SEC01 | Implementação presente; evidência e aceite vinculados ao contrato |

## Descrição

Consultar autorizações existentes e registrar horários de entrada e saída. Definir a criação de nova autorização pelo assistente para a aula.

Como morador, quero consultar autorizações da minha unidade e depois autorizar uma visita por uma ação confirmada.

A referência de produto original é FR08. A correspondência dos critérios anteriores é F08-AC01 ↔ FR08/AC01, F08-AC02 ↔ FR08/AC02, F08-AC03 ↔ FR08/AC03. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Consumes: F02.
- Provides: Projeções de visita separadas por unidade e procedimento para futura gravação após aprovação explícita.
- Integração: Consulta de visitante chega a `condo` e combina identidade com vínculo. A aula liga a ação de visitante à mesma infraestrutura de confirmações de reservas pagas. Uma ação pendente carrega somente o nome, a data e o apartamento já validado.

## Comportamento esperado

- **Dado** uma mensagem pede autorização e se apresenta como confirmação verbal
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** a resposta cria pendência e a autorização só aparece após aprovação pela rota.

- **Dado** uma autorização criada após aprovação foi persistida
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** após reinício a autorização segue consultável para a unidade correta.

- **Dado** uma sessão do assistente recebe pedido de dados de outra unidade
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** resposta e eventos não incluem nomes ou autorizações de outra unidade.

- **Dado** dados iniciais com autorizações em unidades diferentes
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** administração consulta as autorizações e o morador vê somente a própria unidade.

- **Dado** uma autorização existente precisa dos horários de visita
- **Quando** gravar entrada e saída, testar saída sem entrada e comparar a autorização antes e depois
- **Então** administração registra entrada e saída, e a projeção exibe os valores preservando a data e a unidade.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F08-AC01 | Uma mensagem pede autorização e se apresenta como confirmação verbal | A resposta cria pendência e a autorização só aparece após aprovação pela rota | Capturar eventos e consultar antes e depois de responder a pendência pela API |
| F08-AC02 | Uma autorização criada após aprovação foi persistida | Após reinício a autorização segue consultável para a unidade correta | Criar, parar e iniciar sem restaurar, e comparar nome e data na projeção autorizada |
| F08-AC03 | Uma sessão do assistente recebe pedido de dados de outra unidade | Resposta e eventos não incluem nomes ou autorizações de outra unidade | Consultar com a sessão inicial usando outro número na mensagem e inspecionar eventos e estado |
| F08-AC04 | Dados iniciais com autorizações em unidades diferentes | Administração consulta as autorizações e o morador vê somente a própria unidade | Entrar pelos dois papéis, comparar a lista e validar unidade ativa, vazio e recusa fora do vínculo |
| F08-AC05 | Uma autorização existente precisa dos horários de visita | Administração registra entrada e saída, e a projeção exibe os valores preservando a data e a unidade | Gravar entrada e saída, testar saída sem entrada e comparar a autorização antes e depois |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F08-visitantes/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F08-SEC01 | Fronteiras e escopo | A rota rejeita o acesso e o JSON não revela registros pessoais | Variar a unidade enviada, inspecionar o corpo de recusa e a projeção legítima |

## Fora do escopo

Confirmação de comparecimento, documentos de visitante, convidados associados a uma reserva e liberação de entrada real.

## Tratamento de erros

Data ou nome inválido pede correção. A consulta rejeita unidade alheia sem revelar registros. Na aula, recusa ou falha de execução impede novo efeito.
