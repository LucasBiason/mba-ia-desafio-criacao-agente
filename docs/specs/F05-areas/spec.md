---
spec_template: 1
feature: F05
ceremony: full
prd_source: docs/prd/functional/F05-areas.md
---

# F05 — Cadastro de áreas comuns

## 1. Visão técnica

O administrador cria uma área identificada por chave estável, edita nome e taxa e remove uma área sem vínculos. A interface mostra o valor em reais. O serviço processa centavos inteiros e classifica zero como gratuito.

A intenção de produto, as regras e os marcos de aceite vêm do [requisito F05](../../prd/functional/F05-areas.md). As decisões de composição e a separação de responsabilidades estão na [arquitetura](../../arquitetura.md). Este documento especifica os contratos da base e das etapas da aula identificadas na matriz.

## 2. Impacto arquitetural

React usa `condo` para gestão e leitura. A persistência de áreas fica no banco do domínio. O catálogo autenticado alimenta filtros de agenda e seleção de área em atividades futuras do morador.

## 3. Decisões técnicas

Representar preços por `fee_cents` inteiro entre 0 e 100000000. O ID de rota estável usa letras minúsculas, dígitos e hífens, com até 64 caracteres. O nome é único sem distinção de maiúsculas. Em colisão de nome ou identificador, a transação faz rollback e responde 409. A exclusão sujeita-se às referências históricas.

## 4. Visão de componentes

- Formulário administrativo com identificador, nome e taxa.
- API de escrita administrativa e catálogo autenticado de leitura.
- Repositório de áreas e validação de chave, taxa e referências.

## 5. Contratos de interface

GET e POST em `/api/admin/areas` com objetos `id`, `name`, `fee_cents`. GET, PATCH e DELETE em `/api/admin/areas/{id}`. PATCH aceita nome e taxa. GET `/api/areas` retorna catálogo para perfis autenticados. Valor menor que zero ou moeda inválida falha sem persistência.

Chave repetida causa conflito, valor negativo rejeita o cadastro e área referenciada não é removida. A agenda permanece íntegra após recusa.

## 6. Modelo de dados

Área possui chave, nome e centavos não negativos. A carga inicial converte a taxa original em reais dos dados sem editar a fixture. Reserva referencia a área; o efeito financeiro da confirmação pertence à etapa de agentes.

## 7. Estratégia de testes

O [contrato](contract.md) organiza as verificações por critério. Use credenciais locais e massa descartável. **Base** é o comportamento especificado para a aplicação preparada. **Aula do agente** e **Avaliação acadêmica** identificam os testes das etapas guiadas. O [registro de validação](../../validacao.md) indica quais verificações foram de fato executadas.

| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F05-AC01 | Base. Cadastrar a área, abrir o catálogo do morador e comparar `fee_cents` com a indicação visual. | A área aparece no catálogo como gratuita. |
| F05-AC02 | Base. Enviar valores inválidos e consultar a área no catálogo depois. | A requisição é rejeitada e a taxa existente permanece. |
| F05-AC03 | Base. Autenticar como morador, tentar PATCH na rota administrativa e consultar o catálogo. | A operação é recusada e a resposta seguinte preserva o valor. |
| F05-AC04 | Base. Executar as duas exclusões, comparar catálogo e consultar agenda da área referenciada. | A primeira exclusão é recusada e a segunda remove o cadastro independente. |
| F05-SEC01 | Base. Consultar as rotas de catálogo e administração sem bearer. | A API recusa o acesso autenticado sem revelar detalhes internos. |
| NFR01-AC01 | Base. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. | A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. |
| NFR02-AC01 | Base. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. | Efeito confirmado permanece. A falha é observável e o domínio fica consistente. |

### Situação da execução

Implementada; aceite de entrega pendente. Cadastro e taxa de áreas, edição e exclusão protegida. Fonte do código: `services/domain/app.py; web/src/admin.jsx`. As evidências disponíveis são tests/test_api.py — áreas e agenda. Esta revisão é retrospectiva e não atesta a ordem histórica de invocação das skills. Critérios de aula e avaliação continuam pendentes. A [entrega](../../entrega-01.md) concentra o fechamento.

Revisão das fontes: índice atualizado com F11–F14 conferido; IDs e dependências de domínio anteriores preservados.

Conferência final: comportamentos do requisito vinculados aos procedimentos de aceite e situação da primeira entrega.
