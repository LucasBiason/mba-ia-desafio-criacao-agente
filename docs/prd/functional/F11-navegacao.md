# F11 — Navegação responsiva por perfil

Domínio: Interface | Onda: 3 | Prioridade: 1

Conforms to: NFR01, NFR03

## Descrição

Oferecer acesso aos caminhos autorizados por perfil, com barra lateral compacta no desktop e menu modal no celular.

## Capacidades

- Consumes: F03.
- Provides: Oferecer acesso aos caminhos autorizados por perfil, com barra lateral compacta no desktop e menu modal no celular.

## Comportamento esperado

- **Dado** Um administrador ou morador autenticado
- **Quando** abrir seu portal
- **Então** o menu mostra itens correspondentes ao perfil, ícones, nomes acessíveis e estado ativo.

- **Dado** Uma tela com pelo menos 721 px
- **Quando** recolher e expandir o menu
- **Então** o espaço do conteúdo acompanha o menu e todos os links conservam nomes acessíveis.

- **Dado** Uma tela com até 720 px
- **Quando** abrir o menu, navegar, usar Escape ou tocar fora
- **Então** o menu sobreposto fecha, permite navegação por teclado e não ocupa permanentemente o conteúdo.

- **Dado** Menu aberto em celular
- **Quando** navegar pelo teclado e selecionar uma rota
- **Então** o foco fica no diálogo durante a interação e chega ao conteúdo após a seleção.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F11-AC01 | Um administrador ou morador autenticado; abrir seu portal | o menu mostra itens correspondentes ao perfil, ícones, nomes acessíveis e estado ativo. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |
| F11-AC02 | Uma tela com pelo menos 721 px; recolher e expandir o menu | o espaço do conteúdo acompanha o menu e todos os links conservam nomes acessíveis. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |
| F11-AC03 | Uma tela com até 720 px; abrir o menu, navegar, usar Escape ou tocar fora | o menu sobreposto fecha, permite navegação por teclado e não ocupa permanentemente o conteúdo. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |
| F11-AC04 | Menu aberto em celular; navegar pelo teclado e selecionar uma rota | o foco fica no diálogo durante a interação e chega ao conteúdo após a seleção. | Executar a jornada no perfil correspondente e comparar a saída com a API quando aplicável |

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F11-SEC01 | Autorização | API mantém autorização mesmo se o cliente alterar o hash ou o HTML. | Repetir a chamada direta com identidade de outro papel e conferir status e ausência de dados |

## Fora do escopo

Mutações adicionais de domínio e integração do agente.

## Tratamento de erros

Falha da API mostra retorno recuperável. Sessão recusada conduz à entrada. O estado de carregamento precede a apresentação dos dados.
