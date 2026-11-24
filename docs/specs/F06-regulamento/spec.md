---
spec_template: 1
feature: F06
ceremony: full
prd_source: docs/prd/functional/F06-regulamento.md
---

# F06 — Regulamento único e versionado

## 1. Visão técnica

A instalação lê o Markdown original como versão zero. O administrador edita a revisão vigente e informa a versão-base. Uma publicação cria nova linha e preserva cada versão anterior. O morador consulta apenas a versão vigente.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F06](../../prd/functional/F06-regulamento.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

A edição sai do painel autenticado e chega ao domínio. A operação registra na mesma gravação o texto, a versão, a autoridade e o instante. A consulta por assunto recupera a versão publicada e só entrega o trecho relevante. Se não encontrar regra específica, a resposta informa a limitação sem inventar prazo, multa ou gratuidade. A consulta não executa uma ação.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0002](../../adr/ADR-0002-orm-e-integridade-transacional.md), [ADR-0005](../../adr/ADR-0005-regulamento-unico-versionado.md).

Usar versões numeradas e comparar a versão-base no momento da publicação. Esse controle evita que uma edição antiga sobrescreva o trabalho de outra conta. A leitura de conteúdo no frontend preserva texto e não executa marcação recebida do usuário.

## 4. Visão de componentes

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Router | services/parameters/routers/regulation_router.py | Receber DTO e identidade e chamar o controller |
| Controller | services/parameters/controllers/regulation_controller.py | Coordenar validação, persistência e serialização |
| Validator | services/parameters/validators/regulation_validator.py | Verificar permissão e regras da operação |
| Repository | services/parameters/repositories/regulation_repository.py | Consultar e escrever com SQLAlchemy em transação |
| Serializer | services/parameters/serializers/regulation_serializer.py | Produzir DTO público sem campos internos |
| Composição | services/parameters/main.py | Montar routers, middleware, Swagger e health do toolkit |

As schemas Pydantic validam tipo e formato. Validators não gravam e controllers não acessam Session ou engine. O repository aplica flush, locks e constraints conforme a operação. Falha faz rollback. A documentação OpenAPI declara os contratos de entrada, saída, erros e autenticação.

## 5. Contratos de interface

GET `/api/admin/regulation` devolve a versão vigente. PUT na mesma rota recebe `base_version` e `content`. GET `/api/admin/regulation/versions` devolve histórico ordenado. O formato expõe `version`, `content`, `author_id`, `author_name` e `published_at`. GET `/api/resident/regulation` disponibiliza apenas a revisão vigente.

Versão-base desatualizada retorna 409 e a revisão vigente continua disponível para nova tentativa. Conteúdo vazio é recusado. Falha de gravação não publica versão parcial.

## 6. Modelo de dados

Versão é chave numérica crescente. Cada revisão tem conteúdo, autoria pública e instante de publicação. A versão zero tem origem na fixture. Conteúdo anterior continua disponível à administração; exclusão de versão e publicação parcial ficam fora da atualização.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F06-AC01 | Base. Salvar o novo texto, abrir a versão atual e comparar ambas as entradas no histórico. | A versão um fica vigente com autoria e hora, e a versão zero permanece no histórico. |
| F06-AC02 | Base. Enviar duas edições com a mesma versão-base e conferir que foi criada uma única revisão. | A atualização desatualizada retorna conflito e preserva o conteúdo vigente. |
| F06-AC03 | Base. Consultar o texto vigente como morador, tentar PUT na rota admin e comparar versões. | O acesso de escrita é recusado sem alteração do histórico. |
| F06-AC04 | Base. Publicar alteração, reiniciar o domínio e comparar o histórico com a captura anterior. | A versão e o autor permanecem consultáveis após o reinício. |
| F06-SEC01 | Base. Consultar ambos os caminhos e verificar o papel exigido. | A leitura vigente funciona e o histórico administrativo não é entregue ao morador. |
| NFR02-AC01 | Base: HTTP real e reinício. Dado QA_ADMIN leu a versão V do regulamento vigente; quando publicar um texto sintético novo em PUT /api/admin/regulation com base_version=V; reiniciar parameters e ler vigente e /versions. | Então vigente permanece V+1 e histórico conserva V e V+1 com o texto e autor publicados. |
| NFR03-AC01 | Base: HTTP real. Dado QA_A é resident e QA_ADMIN publicou o texto sintético; quando consultar GET /api/resident/regulation e GET /api/admin/regulation/versions usando QA_A. | Então vigente retorna 200 sem credenciais; histórico administrativo retorna 403 sem revisões de autoria alheia. |
