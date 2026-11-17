# Contrato de verificação — F04 — Gestão de usuários e perfis

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F04-01** (P0D, cobre F04-AC01) — Um administrador autenticado e dados de um novo morador. Criar a conta pelo painel, autenticar, confirmar formato público e vincular unidade -> O cadastro devolve perfil público, aceita login da nova conta e permite vinculá-la. Modo: Base.
- **E2E-F04-02** (P0D, cobre F04-AC02) — O último administrador ativo sofre tentativa de desativação. Em ambiente isolado, desativar as outras contas administrativas e tentar desativar a última -> A operação é recusada e uma conta administrativa continua ativa. Modo: Base.
- **E2E-F04-03** (P0D, cobre F04-AC03) — Um morador com sessão válida tenta acessar outro perfil ou a lista administrativa. Pedir lista administrativa e perfil próprio e inspecionar apenas a identidade autenticada -> A resposta não inclui registros alheios. Modo: Base.
- **E2E-F04-04** (P0D, cobre F04-AC04) — Uma conta existente. Atualizar uma conta criada para o teste, repetir email em segunda conta, desativar e reapresentar token -> Edição persiste e a desativação invalida o acesso; duplicidade é rejeitada. Modo: Base.
- **E2E-F04-05** (P0D, cobre F04-SEC01) — Cadastro, edição e erro de duplicidade. Inspecionar respostas válidas e de erro com credenciais descartáveis -> O JSON e a evidência não incluem senha ou hash. Modo: Base.
- **E2E-F04-06** (P0D, cobre NFR01-AC01) — Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável -> A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. Modo: Base.
- **E2E-F04-07** (P0D, cobre NFR03-AC01) — Operação privada bem-sucedida ou recusada. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas -> A evidência não inclui segredos ou objetos de unidades fora da autorização. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F04-01 | F04-AC01 | Base |
| E2E-F04-02 | F04-AC02 | Base |
| E2E-F04-03 | F04-AC03 | Base |
| E2E-F04-04 | F04-AC04 | Base |
| E2E-F04-05 | F04-SEC01 | Base |
| E2E-F04-06 | NFR01-AC01 | Base |
| E2E-F04-07 | NFR03-AC01 | Base |

A cobertura é uma previsão. O [registro de validação](../../validacao.md) distingue provas executadas, verificações documentais e etapas ainda dependentes da prática.

## Resultado disponível

A [validação](../../validacao.md) registra execuções anteriores por superfície. O contrato conserva os critérios que ainda exigem prova. Esta atualização documental não equivale à execução de todos os itens P0D. Conferir a [matriz de entrega](../../entrega-01.md) antes de promover o estado da funcionalidade.
