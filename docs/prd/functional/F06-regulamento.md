# F06 — Regulamento único e versionado

Domínio: Administração | Onda: 3 | Prioridade: 1

Requisitos não funcionais relacionados: NFR02, NFR03

## Descrição

Exibir o texto vigente, publicar um histórico ordenado e imutável e rejeitar edição concorrente sobre base desatualizada.

Como administrador, quero publicar novas versões do regulamento e saber quem alterou cada versão e quando.

A referência de produto original é FR06. A correspondência dos critérios anteriores é F06-AC01 ↔ FR06/AC01, F06-AC02 ↔ FR06/AC02, F06-AC03 ↔ FR06/AC03. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Depende de: F03.
- Fornece: Conteúdo vigente para o morador e um histórico administrativo com autoria e horário de publicação.
- Integração: A edição sai do painel autenticado e chega ao domínio. A operação registra na mesma gravação o texto, a versão, a autoridade e o instante. A futura consulta por assunto usa o texto vigente, por meio de uma ferramenta proposta no roteiro.

## Comportamento esperado

- **Dado** um administrador edita a versão zero ativa
- **Quando** salvar o novo texto, abrir a versão atual e comparar ambas as entradas no histórico
- **Então** a versão um fica vigente com autoria e hora, e a versão zero permanece no histórico.

- **Dado** duas contas editam a mesma versão-base
- **Quando** enviar duas edições com a mesma versão-base e conferir que foi criada uma única revisão
- **Então** a atualização desatualizada retorna conflito e preserva o conteúdo vigente.

- **Dado** um morador autenticado tenta publicar uma edição
- **Quando** consultar o texto vigente como morador, tentar PUT na rota admin e comparar versões
- **Então** o acesso de escrita é recusado sem alteração do histórico.

- **Dado** uma revisão publicada antes de reiniciar o serviço
- **Quando** publicar alteração, reiniciar o domínio e comparar o histórico com a captura anterior
- **Então** a versão e o autor permanecem consultáveis após o reinício.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F06-AC01 | Um administrador edita a versão zero ativa | A versão um fica vigente com autoria e hora, e a versão zero permanece no histórico | Salvar o novo texto, abrir a versão atual e comparar ambas as entradas no histórico |
| F06-AC02 | Duas contas editam a mesma versão-base | A atualização desatualizada retorna conflito e preserva o conteúdo vigente | Enviar duas edições com a mesma versão-base e conferir que foi criada uma única revisão |
| F06-AC03 | Um morador autenticado tenta publicar uma edição | O acesso de escrita é recusado sem alteração do histórico | Consultar o texto vigente como morador, tentar PUT na rota admin e comparar versões |
| F06-AC04 | Uma revisão publicada antes de reiniciar o serviço | A versão e o autor permanecem consultáveis após o reinício | Publicar alteração, reiniciar o domínio e comparar o histórico com a captura anterior |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F06-regulamento/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F06-SEC01 | Fronteiras e escopo | A leitura vigente funciona e o histórico administrativo não é entregue ao morador | Consultar ambos os caminhos e verificar o papel exigido |

## Fora do escopo

Edição colaborativa em tempo real, múltiplos regulamentos e exclusão de versões.

## Tratamento de erros

Versão-base desatualizada retorna 409 e a revisão vigente continua disponível para nova tentativa. Conteúdo vazio é recusado. Falha de gravação não publica versão parcial.
