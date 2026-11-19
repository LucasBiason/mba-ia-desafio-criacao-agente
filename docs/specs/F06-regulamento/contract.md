# Contrato de verificação — F06 — Regulamento único e versionado

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F06-01** (P0D, cobre F06-AC01) — Um administrador edita a versão zero ativa. Salvar o novo texto, abrir a versão atual e comparar ambas as entradas no histórico -> A versão um fica vigente com autoria e hora, e a versão zero permanece no histórico. Modo: Base.
- **E2E-F06-02** (P0D, cobre F06-AC02) — Duas contas editam a mesma versão-base. Enviar duas edições com a mesma versão-base e conferir que foi criada uma única revisão -> A atualização desatualizada retorna conflito e preserva o conteúdo vigente. Modo: Base.
- **E2E-F06-03** (P0D, cobre F06-AC03) — Um morador autenticado tenta publicar uma edição. Consultar o texto vigente como morador, tentar PUT na rota admin e comparar versões -> O acesso de escrita é recusado sem alteração do histórico. Modo: Base.
- **E2E-F06-04** (P0D, cobre F06-AC04) — Uma revisão publicada antes de reiniciar o serviço. Publicar alteração, reiniciar o domínio e comparar o histórico com a captura anterior -> A versão e o autor permanecem consultáveis após o reinício. Modo: Base.
- **E2E-F06-05** (P0D, cobre F06-SEC01) — Uma conta moradora solicita a versão vigente ou a rota de histórico admin. Consultar ambos os caminhos e verificar o papel exigido -> A leitura vigente funciona e o histórico administrativo não é entregue ao morador. Modo: Base.
- **E2E-F06-06** (P0D, cobre NFR02-AC01) — Reinício da dependência, corrida de gravação ou falha antes de concluir a escrita. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita -> Efeito confirmado permanece. A falha é observável e o domínio fica consistente. Modo: Base.
- **E2E-F06-07** (P0D, cobre NFR03-AC01) — Operação privada bem-sucedida ou recusada. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas -> A evidência não inclui segredos ou objetos de unidades fora da autorização. Modo: Base.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F06-01 | F06-AC01 | Base |
| E2E-F06-02 | F06-AC02 | Base |
| E2E-F06-03 | F06-AC03 | Base |
| E2E-F06-04 | F06-AC04 | Base |
| E2E-F06-05 | F06-SEC01 | Base |
| E2E-F06-06 | NFR02-AC01 | Base |
| E2E-F06-07 | NFR03-AC01 | Base |
