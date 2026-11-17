---
spec_template: 1
feature: F06
ceremony: full
prd_source: docs/prd/functional/F06-regulamento.md
---

# F06 — Regulamento único e versionado

## 1. Visão técnica

A instalação lê o Markdown original como versão zero. O administrador edita a revisão vigente e informa a versão-base. Uma publicação cria nova linha e preserva cada versão anterior. O morador consulta apenas a versão vigente.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F06](../../prd/functional/F06-regulamento.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../arquitetura.md). Este documento especifica os contratos da base e das etapas da aula identificadas na matriz.

## 2. Impacto arquitetural

A edição sai do painel autenticado e chega ao domínio. A operação registra na mesma gravação o texto, a versão, a autoridade e o instante. A futura consulta por assunto usa o texto vigente, por meio de uma ferramenta proposta no roteiro.

## 3. Decisões técnicas

Usar versões numeradas e comparar a versão-base no momento da publicação. Esse controle evita que uma edição antiga sobrescreva o trabalho de outra conta. A leitura de conteúdo no frontend preserva texto e não executa marcação recebida do usuário.

## 4. Visão de componentes

- Painel administrativo com editor, estado vigente e lista de versões.
- Tela do morador com texto vigente e versão publicada.
- Repositório de revisões com proteção contra conflito e importação inicial do Markdown.

## 5. Contratos de interface

GET `/api/admin/regulation` devolve a versão vigente. PUT na mesma rota recebe `base_version` e `content`. GET `/api/admin/regulation/versions` devolve histórico ordenado. O formato expõe `version`, `content`, `author_id`, `author_name` e `published_at`. GET `/api/resident/regulation` disponibiliza apenas a revisão vigente.

Versão-base desatualizada retorna 409 e a revisão vigente continua disponível para nova tentativa. Conteúdo vazio é recusado. Falha de gravação não publica versão parcial.

## 6. Modelo de dados

Versão é chave numérica crescente. Cada revisão tem conteúdo, autoria pública e instante de publicação. A versão zero tem origem na fixture. Conteúdo anterior continua disponível à administração; exclusão de versão e publicação parcial ficam fora da atualização.

## 7. Estratégia de testes

O [contrato](contract.md) organiza as verificações por critério. Use credenciais locais e massa descartável. **Base** é o comportamento especificado para a aplicação preparada. **Aula do agente** e **Avaliação acadêmica** identificam os testes das etapas guiadas. O [registro de validação](../../validacao.md) indica quais verificações foram de fato executadas.

| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F06-AC01 | Base. Salvar o novo texto, abrir a versão atual e comparar ambas as entradas no histórico. | A versão um fica vigente com autoria e hora, e a versão zero permanece no histórico. |
| F06-AC02 | Base. Enviar duas edições com a mesma versão-base e conferir que foi criada uma única revisão. | A atualização desatualizada retorna conflito e preserva o conteúdo vigente. |
| F06-AC03 | Base. Consultar o texto vigente como morador, tentar PUT na rota admin e comparar versões. | O acesso de escrita é recusado sem alteração do histórico. |
| F06-AC04 | Base. Publicar alteração, reiniciar o domínio e comparar o histórico com a captura anterior. | A versão e o autor permanecem consultáveis após o reinício. |
| F06-SEC01 | Base. Consultar ambos os caminhos e verificar o papel exigido. | A leitura vigente funciona e o histórico administrativo não é entregue ao morador. |
| NFR02-AC01 | Base. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. | Efeito confirmado permanece. A falha é observável e o domínio fica consistente. |
| NFR03-AC01 | Base. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas. | A evidência não inclui segredos ou objetos de unidades fora da autorização. |

### Situação da execução

Implementada; aceite de entrega pendente. Regulamento vigente, edição, histórico e conflito de versão. Fonte do código: `services/domain/app.py; web/src/admin.jsx`. As evidências disponíveis são tests/test_api.py — versões; validação prévia de concorrência. Esta revisão é retrospectiva e não atesta a ordem histórica de invocação das skills. Critérios de aula e avaliação continuam pendentes. A [entrega](../../entrega-01.md) concentra o fechamento.

Revisão das fontes: índice atualizado com F11–F14 conferido; IDs e dependências de domínio anteriores preservados.

Conferência final: comportamentos do requisito vinculados aos procedimentos de aceite e situação da primeira entrega.
