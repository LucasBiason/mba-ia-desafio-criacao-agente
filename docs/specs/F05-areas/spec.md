---
spec_template: 1
feature: F05
ceremony: full
prd_source: docs/prd/functional/F05-areas.md
---

# F05 — Cadastro de áreas comuns

## 1. Visão técnica

O administrador cria uma área identificada por chave estável, edita nome e taxa e remove uma área sem vínculos. A interface mostra o valor em reais. O serviço processa centavos inteiros e classifica zero como gratuito.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F05](../../prd/functional/F05-areas.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../design/architecture.md). Este documento especifica os contratos da base e das etapas da integração identificadas na matriz.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

React usa a aplicação `common-areas` para gestão e leitura. A persistência de áreas fica no banco do domínio. O catálogo autenticado alimenta filtros de agenda e seleção de área em atividades futuras do morador.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0001](../../adr/ADR-0001-servicos-por-dominio-e-camadas.md), [ADR-0002](../../adr/ADR-0002-orm-e-integridade-transacional.md).

Representar preços por `fee_cents` inteiro entre 0 e 100000000. O ID de rota estável usa letras minúsculas, dígitos e hífens, com até 64 caracteres. O nome é único sem distinção de maiúsculas. Em colisão de nome ou identificador, a transação faz rollback e responde 409. A exclusão sujeita-se às referências históricas.

## 4. Visão de componentes

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Router | services/common_areas/routers/area_router.py | Receber DTO e identidade e chamar o controller |
| Controller | services/common_areas/controllers/area_controller.py | Coordenar validação, persistência e serialização |
| Validator | services/common_areas/validators/area_validator.py | Verificar permissão e regras da operação |
| Repository | services/common_areas/repositories/area_repository.py | Consultar e escrever com SQLAlchemy em transação |
| Serializer | services/common_areas/serializers/area_serializer.py | Produzir DTO público sem campos internos |
| Composição | services/common_areas/main.py | Montar routers, middleware, Swagger e health do toolkit |

As schemas Pydantic validam tipo e formato. Validators não gravam e controllers não acessam Session ou engine. O repository aplica flush, locks e constraints conforme a operação. Falha faz rollback. A documentação OpenAPI declara os contratos de entrada, saída, erros e autenticação.

## 5. Contratos de interface

GET e POST em `/api/admin/areas` com objetos `id`, `name`, `fee_cents`. GET, PATCH e DELETE em `/api/admin/areas/{id}`. PATCH aceita nome e taxa. GET `/api/areas` retorna catálogo para perfis autenticados. Valor menor que zero ou moeda inválida falha sem persistência.

Chave repetida causa conflito, valor negativo rejeita o cadastro e área referenciada não é removida. A agenda permanece íntegra após recusa.

## 6. Modelo de dados

Área possui chave, nome e centavos não negativos. A carga inicial converte a taxa original em reais dos dados sem editar a fixture. Reserva referencia a área; o efeito financeiro da confirmação pertence à etapa de agentes.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F05-AC01 | Base. Cadastrar a área, abrir o catálogo do morador e comparar `fee_cents` com a indicação visual. | A área aparece no catálogo como gratuita. |
| F05-AC02 | Base. Enviar valores inválidos e consultar a área no catálogo depois. | A requisição é rejeitada e a taxa existente permanece. |
| F05-AC03 | Base. Autenticar como morador, tentar PATCH na rota administrativa e consultar o catálogo. | A operação é recusada e a resposta seguinte preserva o valor. |
| F05-AC04 | Base. Executar as duas exclusões, comparar catálogo e consultar agenda da área referenciada. | A primeira exclusão é recusada e a segunda remove o cadastro independente. |
| F05-SEC01 | Base. Consultar as rotas de catálogo e administração sem bearer. | A API recusa o acesso autenticado sem revelar detalhes internos. |
| NFR01-AC01 | Base: HTTP real. Dado QA_AREA existe com fee_cents=100 e QA_A é resident; quando enviar PATCH /api/admin/areas/{QA_AREA} com fee_cents=200 usando QA_A e reler como QA_ADMIN. | Então HTTP 403 e taxa original 100 preservada. |
| NFR02-AC01 | Base: HTTP real e reinício. Dado QA_AREA foi criada por QA_ADMIN com fee_cents=100; quando reiniciar common-areas e condo-db sem restore e consultar GET /api/admin/areas/{QA_AREA}. | Então HTTP 200 com o mesmo id, nome e taxa 100, sem segunda área. |
