# Contrato de verificação — F03 — Autenticação e autorização

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F03-01** (P0D, cobre F03-AC01) — Uma conta ativa com credenciais válidas. Autenticar administrador e morador e consultar o perfil e a superfície privada permitida -> Login devolve uma sessão JWT aceito na leitura privada apropriada ao papel. Modo: Base.
- **E2E-F03-02** (P0D, cobre F03-AC02) — Uma rota privada acessada com token ausente, vencido, adulterado ou revogado. Variar os quatro estados com massa efêmera, comparar as respostas e conferir a persistência -> O acesso retorna 401 sem executar a operação. Modo: Base.
- **E2E-F03-03** (P0D, cobre F03-AC03) — Um morador com sessão válida em rota administrativa. Enviar o mesmo POST como administrador e morador, comparar estados e status -> O acesso retorna 403 sem efetivar mutação. Modo: Base.
- **E2E-F03-04** (P0D, cobre F03-AC04) — A identidade centralizada indisponível em teste isolado. Induzir falha da introspecção, obter 503 e comparar o estado após reativar o serviço -> O consumidor devolve erro de dependência e não executa a ação. Modo: Base.
- **E2E-F03-05** (P0D, cobre F03-SEC01) — Uma sessão autenticada encerrada pelo usuário. Fazer logout, retomar a rota privada e reapresentar o bearer anterior -> A sessão perde validade no servidor e o navegador retorna ao login. Modo: Base.
- **E2E-F03-06** (P0D, cobre F03-SEC02) — Login com senha errada ou conta inexistente. Comparar corpo e status dos erros e revisar o conteúdo do registro da aplicação -> A resposta recusa acesso sem confirmar a existência da conta ou revelar segredo. Modo: Base.
- **E2E-F03-07** (P0D, cobre NFR01-AC01) — Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável -> A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. Modo: Base.
- **E2E-F03-08** (P0D, cobre NFR03-AC01) — Operação privada bem-sucedida ou recusada. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas -> A evidência não inclui segredos ou objetos de unidades fora da autorização. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F03-01 | F03-AC01 | Base |
| E2E-F03-02 | F03-AC02 | Base |
| E2E-F03-03 | F03-AC03 | Base |
| E2E-F03-04 | F03-AC04 | Base |
| E2E-F03-05 | F03-SEC01 | Base |
| E2E-F03-06 | F03-SEC02 | Base |
| E2E-F03-07 | NFR01-AC01 | Base |
| E2E-F03-08 | NFR03-AC01 | Base |

A cobertura é uma previsão. O [registro de validação](../../validacao.md) distingue provas executadas, verificações documentais e etapas ainda dependentes da prática.

## Resultado disponível

A [validação](../../validacao.md) registra execuções anteriores por superfície. O contrato conserva os critérios que ainda exigem prova. Esta atualização documental não equivale à execução de todos os itens P0D. Conferir a [matriz de entrega](../../entrega-01.md) antes de promover o estado da funcionalidade.
