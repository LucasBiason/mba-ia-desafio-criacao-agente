# Contrato de verificação — F10 — Compatibilidade e aceite acadêmico

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F10-01** (P0D, cobre F10-AC01) — Um clone limpo com dependências e chave própria autorizada. Seguir o roteiro de partida, restaurar os dados, registrar códigos e observar estado e eventos em cada passo -> O avaliador executa os 15 passos na porta 8000 com o protocolo completo. Modo: Avaliação acadêmica.
- **E2E-F10-02** (P0D, cobre F10-AC02) — A composição base do produto é consultada pelo proxy publicado. Consultar rotas locais planejadas na origem do produto e tentar APIs privadas sem bearer -> Caminhos acadêmicos e rotas internas não contornam a autenticação. Modo: Base.
- **E2E-F10-03** (P0D, cobre F10-AC03) — O fork está em preparação final após a aula. Comparar hashes dos dados, revisar o lock e verificar os links das garantias -> Cinco fixtures correspondem à origem e o README identifica provas e trechos implementados. Modo: Avaliação acadêmica.
- **E2E-F10-04** (P0D, cobre F10-AC04) — A base é construída e iniciada com seu comando de demonstração. Conferir os hashes das fixtures antes da partida e depois do teste com volumes isolados -> As cinco fixtures mantêm o mesmo conteúdo entre a cópia e o ambiente inicializado. Modo: Base.
- **E2E-F10-05** (P0D, cobre F10-SEC01) — O modo avaliador é iniciado numa composição descartável. Conferir bind, isolamento de armazenamento, rota de autenticação do produto e diff de configuração -> O exercício roda localmente, com dados separados e sem publicar segredos. Modo: Avaliação acadêmica.
- **E2E-F10-06** (P0D, cobre NFR01-AC01) — Token ou papel inadequado, acesso fora do vínculo ou ação sensível sem decisão. Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável -> A fronteira recusa acesso ou mantém a ação pendente conforme o caso. A operação indevida não altera estado. Modo: Avaliação acadêmica.
- **E2E-F10-07** (P0D, cobre NFR03-AC01) — Operação privada bem-sucedida ou recusada. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas -> A evidência não inclui segredos ou objetos de unidades fora da autorização. Modo: Avaliação acadêmica.
- **E2E-F10-08** (P0D, cobre NFR04-AC01) — Execução da base ou execução isolada do protocolo acadêmico. Executar o procedimento aplicável a partir de uma instalação isolada e registrar componentes, saídas e condições não exercitadas -> As dependências do modo escolhido atingem prontidão e os verificadores registram a condição observada. Modo: Avaliação acadêmica.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F10-01 | F10-AC01 | Avaliação acadêmica |
| E2E-F10-02 | F10-AC02 | Base |
| E2E-F10-03 | F10-AC03 | Avaliação acadêmica |
| E2E-F10-04 | F10-AC04 | Base |
| E2E-F10-05 | F10-SEC01 | Avaliação acadêmica |
| E2E-F10-06 | NFR01-AC01 | Avaliação acadêmica |
| E2E-F10-07 | NFR03-AC01 | Avaliação acadêmica |
| E2E-F10-08 | NFR04-AC01 | Avaliação acadêmica |

A cobertura é uma previsão. O [registro de validação](../../validacao.md) distingue provas executadas, verificações documentais e etapas ainda dependentes da prática.

## Resultado disponível

A [validação](../../validacao.md) registra execuções anteriores por superfície. O contrato conserva os critérios que ainda exigem prova. Esta atualização documental não equivale à execução de todos os itens P0D. Conferir a [matriz de entrega](../../entrega-01.md) antes de promover o estado da funcionalidade.
