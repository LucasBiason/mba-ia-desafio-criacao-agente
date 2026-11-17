# F13 — Visão geral do morador

Domínio: Morador | Onda: 6 | Prioridade: 1

Conforms to: NFR01, NFR03

## Descrição

Mostrar ao morador o resumo de sua unidade selecionada e os caminhos para consultas e assistente.

## Capacidades

- Consumes: F02, F07, F08.
- Provides: Mostrar ao morador o resumo de sua unidade selecionada e os caminhos para consultas e assistente.

## Comportamento esperado

- **Dado** Morador vinculado a uma unidade
- **Quando** abrir o portal e selecionar a unidade
- **Então** o resumo usa somente as reservas e visitas permitidas para essa identidade.

- **Dado** Morador sem unidade vinculada
- **Quando** abrir a visão geral
- **Então** o estado vazio explica o vínculo necessário e não apresenta dados de terceiros.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F13-AC01 | Morador vinculado a uma unidade; abrir o portal e selecionar a unidade | o resumo usa somente as reservas e visitas permitidas para essa identidade. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |
| F13-AC02 | Morador sem unidade vinculada; abrir a visão geral | o estado vazio explica o vínculo necessário e não apresenta dados de terceiros. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F13-SEC01 | Autorização | Parâmetro de apartamento de outra conta é recusado pelo servidor. | Repetir a chamada direta com identidade de outro papel e conferir status e ausência de dados |

## Fora do escopo

Mutações adicionais de domínio e integração do agente.

## Tratamento de erros

Falha da API mostra retorno recuperável. Sessão recusada conduz à entrada. O estado de carregamento precede a apresentação dos dados.
