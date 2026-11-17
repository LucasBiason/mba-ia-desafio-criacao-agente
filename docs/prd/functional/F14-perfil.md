# F14 — Consulta do próprio perfil

Domínio: Conta | Onda: 3 | Prioridade: 1

Conforms to: NFR01, NFR03

## Descrição

Permitir que cada conta confira nome, e-mail e tipo associados à sessão corrente.

## Capacidades

- Consumes: F03.
- Provides: Permitir que cada conta confira nome, e-mail e tipo associados à sessão corrente.

## Comportamento esperado

- **Dado** Uma conta autenticada
- **Quando** selecionar o nome na barra superior
- **Então** a tela Meu perfil apresenta nome, e-mail e tipo da identidade autenticada.

- **Dado** Sessão encerrada
- **Quando** tentar abrir a rota de perfil
- **Então** o portal volta à entrada e a API privada recusa a sessão revogada.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F14-AC01 | Uma conta autenticada; selecionar o nome na barra superior | a tela Meu perfil apresenta nome, e-mail e tipo da identidade autenticada. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |
| F14-AC02 | Sessão encerrada; tentar abrir a rota de perfil | o portal volta à entrada e a API privada recusa a sessão revogada. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F14-SEC01 | Autorização | O perfil é obtido da identidade autenticada, sem aceitar um ID arbitrário da interface. | Repetir a chamada direta com identidade de outro papel e conferir status e ausência de dados |

## Fora do escopo

Mutações adicionais de domínio e integração do agente.

## Tratamento de erros

Falha da API mostra retorno recuperável. Sessão recusada conduz à entrada. O estado de carregamento precede a apresentação dos dados.
