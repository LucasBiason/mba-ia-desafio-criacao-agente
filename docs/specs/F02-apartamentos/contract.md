# Contrato de verificação — F02 — Cadastro de apartamentos

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F02-01** (P0D, cobre F02-AC01) — Um administrador e uma conta moradora ativa e cadastrada. Cadastrar uma unidade, editar uma segunda e consultar a API de unidades com credenciais do morador -> O painel associa duas unidades à mesma conta e ambas aparecem na lista própria do morador. Modo: Base.
- **E2E-F02-02** (P0D, cobre F02-AC02) — Um número já existente. Criar uma unidade, repetir POST com vínculo diferente e comparar o estado obtido por GET -> A tentativa duplicada retorna conflito e preserva a unidade original. Modo: Base.
- **E2E-F02-03** (P0D, cobre F02-AC03) — Um morador autenticado. Tentar criar e editar unidades como morador, em seguida comparar a lista administrativa -> As operações administrativas são recusadas sem persistir alterações. Modo: Base.
- **E2E-F02-04** (P0D, cobre F02-AC04) — Uma unidade usada por reserva ou autorização de visita. Tentar DELETE sobre unidade de fixture com dependência e consultar a unidade e a agenda -> A exclusão é bloqueada e o histórico fica disponível. Modo: Base.
- **E2E-F02-05** (P0D, cobre F02-SEC01) — Uma conta vinculada a uma única unidade. Comparar GET de unidades do morador a duas unidades administrativas -> A consulta pessoal não devolve unidades de outras contas. Modo: Base.
- **E2E-F02-06** (P0D, cobre NFR01-AC01) — Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável -> A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. Modo: Base.
- **E2E-F02-07** (P0D, cobre NFR03-AC01) — Operação privada bem-sucedida ou recusada. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas -> A evidência não inclui segredos ou objetos de unidades fora da autorização. Modo: Base.
- **E2E-F02-08** (P0D, cobre F02-AC05) — Uma unidade da carga inicial e uma unidade editável. Conferir usuários e apartamentos importados e consultar uma unidade de teste após renumerá-la -> A carga associa o usuário morador da fonte à unidade, e o código da unidade editada se mantém após alterar o número. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F02-01 | F02-AC01 | Base |
| E2E-F02-02 | F02-AC02 | Base |
| E2E-F02-03 | F02-AC03 | Base |
| E2E-F02-04 | F02-AC04 | Base |
| E2E-F02-05 | F02-SEC01 | Base |
| E2E-F02-06 | NFR01-AC01 | Base |
| E2E-F02-07 | NFR03-AC01 | Base |
| E2E-F02-08 | F02-AC05 | Base |
