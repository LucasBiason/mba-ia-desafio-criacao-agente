# F05 — Cadastro de áreas comuns

Domínio: Administração | Onda: 3 | Prioridade: 1

Requisitos não funcionais relacionados: NFR02, NFR01

## Descrição

Permitir CRUD de áreas e taxa não negativa, com escopo administrativo e preservação de referências históricas.

Como administrador, quero manter áreas e taxas atualizadas para que morador e agenda consultem o catálogo correto.

A referência de produto original é FR05. A correspondência dos critérios anteriores é F05-AC01 ↔ FR05/AC01, F05-AC02 ↔ FR05/AC02, F05-AC03 ↔ FR05/AC03. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Depende de: F03.
- Fornece: Catálogo autenticado de áreas e frequência de taxa para consulta e futura operação do agente.
- Integração: React usa `condo` para gestão e leitura. A persistência de áreas fica no banco do domínio. O catálogo autenticado alimenta filtros de agenda e seleção de área em atividades futuras do morador.

## Comportamento esperado

- **Dado** um administrador cria área com taxa zero
- **Quando** cadastrar a área, abrir o catálogo do morador e comparar `fee_cents` com a indicação visual
- **Então** a área aparece no catálogo como gratuita.

- **Dado** uma taxa negativa no cadastro ou na edição
- **Quando** enviar valores inválidos e consultar a área no catálogo depois
- **Então** a requisição é rejeitada e a taxa existente permanece.

- **Dado** um morador tenta editar uma taxa
- **Quando** autenticar como morador, tentar PATCH na rota administrativa e consultar o catálogo
- **Então** a operação é recusada e a resposta seguinte preserva o valor.

- **Dado** uma área referenciada e uma área recém-criada sem uso
- **Quando** executar as duas exclusões, comparar catálogo e consultar agenda da área referenciada
- **Então** a primeira exclusão é recusada e a segunda remove o cadastro independente.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F05-AC01 | Um administrador cria área com taxa zero | A área aparece no catálogo como gratuita | Cadastrar a área, abrir o catálogo do morador e comparar `fee_cents` com a indicação visual |
| F05-AC02 | Uma taxa negativa no cadastro ou na edição | A requisição é rejeitada e a taxa existente permanece | Enviar valores inválidos e consultar a área no catálogo depois |
| F05-AC03 | Um morador tenta editar uma taxa | A operação é recusada e a resposta seguinte preserva o valor | Autenticar como morador, tentar PATCH na rota administrativa e consultar o catálogo |
| F05-AC04 | Uma área referenciada e uma área recém-criada sem uso | A primeira exclusão é recusada e a segunda remove o cadastro independente | Executar as duas exclusões, comparar catálogo e consultar agenda da área referenciada |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F05-areas/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F05-SEC01 | Fronteiras e escopo | A API recusa o acesso autenticado sem revelar detalhes internos | Consultar as rotas de catálogo e administração sem bearer |

## Fora do escopo

Pagamentos, estornos, cobrança real e gestão de múltiplos condomínios.

## Tratamento de erros

Chave repetida causa conflito, valor negativo rejeita o cadastro e área referenciada não é removida. A agenda permanece íntegra após recusa.
