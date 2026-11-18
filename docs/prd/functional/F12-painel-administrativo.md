# F12 — Visão geral administrativa

Domínio: Administração | Onda: 6 | Prioridade: 1

Requisitos não funcionais relacionados: NFR01, NFR03

## Descrição

Consolidar os totais de cadastros e os atalhos de gestão para iniciar a operação administrativa.

## Capacidades

- Depende de: F02, F05, F07.
- Fornece: Consolidar os totais de cadastros e os atalhos de gestão para iniciar a operação administrativa.

## Comportamento esperado

- **Dado** Uma conta administrativa e dados carregados
- **Quando** abrir a visão geral
- **Então** o painel mostra totais de apartamentos, áreas e reservas coerentes com as APIs.

- **Dado** Painel administrativo aberto
- **Quando** selecionar um atalho de cadastro ou agenda
- **Então** a rota correspondente abre e o menu identifica o destino ativo.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F12-AC01 | Uma conta administrativa e dados carregados; abrir a visão geral | o painel mostra totais de apartamentos, áreas e reservas coerentes com as APIs. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |
| F12-AC02 | Painel administrativo aberto; selecionar um atalho de cadastro ou agenda | a rota correspondente abre e o menu identifica o destino ativo. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F12-SEC01 | Autorização | Morador não obtém os dados administrativos ao solicitar diretamente suas APIs. | Repetir a chamada direta com identidade de outro papel e conferir status e ausência de dados |

## Fora do escopo

Mutações adicionais de domínio e integração do agente.

## Tratamento de erros

Falha da API mostra retorno recuperável. Sessão recusada conduz à entrada. O estado de carregamento precede a apresentação dos dados.
