# F02 — Cadastro de apartamentos

Domínio: Administração | Onda: 4 | Prioridade: 1

Conforms to: NFR01, NFR03

## Descrição

Cadastrar, consultar, editar o vínculo e remover unidades sem comprometer o histórico do condomínio.

Como administrador, quero identificar o apartamento por seu código e número e atribuir um único morador responsável. Neste exercício o proprietário e o morador responsável são a mesma pessoa. Uma unidade vaga pode ficar sem vínculo.

A referência de produto original é FR02. A correspondência dos critérios anteriores é F02-AC01 ↔ FR02/AC01, F02-AC02 ↔ FR02/AC02, F02-AC03 ↔ FR02/AC03. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Consumes: F04.
- Provides: Unidades com código estável e número único, relacionadas a um único usuário morador quando ocupadas, consumidas pelas agendas, visitas e sessões do chat.
- Integração: Cadastro passa pelo proxy e pelo guard de identidade do serviço de condomínio. A verificação de conta elegível consulta `users` por fronteira interna. Reservas, visitantes e futuros pedidos de agente se referem à unidade registrada no próprio domínio.

## Comportamento esperado

- **Dado** um administrador e uma conta moradora ativa e cadastrada
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** o painel associa duas unidades à mesma conta e ambas aparecem na lista própria do morador.

- **Dado** um número já existente
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** a tentativa duplicada retorna conflito e preserva a unidade original.

- **Dado** um morador autenticado
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** as operações administrativas são recusadas sem persistir alterações.

- **Dado** uma unidade usada por reserva ou autorização de visita
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** a exclusão é bloqueada e o histórico fica disponível.

- **Dado** uma unidade da carga inicial e uma unidade editável
- **Quando** conferir usuários e apartamentos importados e consultar uma unidade de teste após renumerá-la
- **Então** a carga associa o usuário morador da fonte à unidade, e o código da unidade editada se mantém após alterar o número.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F02-AC01 | Um administrador e uma conta moradora ativa e cadastrada | O painel associa duas unidades à mesma conta e ambas aparecem na lista própria do morador | Cadastrar uma unidade, editar uma segunda e consultar a API de unidades com credenciais do morador |
| F02-AC02 | Um número já existente | A tentativa duplicada retorna conflito e preserva a unidade original | Criar uma unidade, repetir POST com vínculo diferente e comparar o estado obtido por GET |
| F02-AC03 | Um morador autenticado | As operações administrativas são recusadas sem persistir alterações | Tentar criar e editar unidades como morador, em seguida comparar a lista administrativa |
| F02-AC04 | Uma unidade usada por reserva ou autorização de visita | A exclusão é bloqueada e o histórico fica disponível | Tentar DELETE sobre unidade de fixture com dependência e consultar a unidade e a agenda |
| F02-AC05 | Uma unidade da carga inicial e uma unidade editável | A carga associa o usuário morador da fonte à unidade, e o código da unidade editada se mantém após alterar o número | Conferir usuários e apartamentos importados e consultar uma unidade de teste após renumerá-la |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F02-apartamentos/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F02-SEC01 | Fronteiras e escopo | A consulta pessoal não devolve unidades de outras contas | Comparar GET de unidades do morador a duas unidades administrativas |

## Fora do escopo

Cadastro de outros ocupantes, distinção entre proprietário e responsável, transferência de histórico, múltiplos condomínios e documentos de morador.

## Tratamento de erros

Número repetido gera conflito. Conta inexistente ou com papel incompatível rejeita o vínculo. A ativação do login é gerenciada separadamente. A tentativa de excluir unidade referenciada preserva os registros dependentes e informa o motivo. A falha da identidade não autoriza a mutação.
