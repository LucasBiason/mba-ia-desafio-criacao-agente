# Plano de implementação — F03 — Autenticação e autorização

## Dependências

Entradas: [requisito do PRD](../../prd/functional/F03-autenticacao.md), [spec](spec.md) e [arquitetura](../../arquitetura.md). Dependências de produto: F01. Os passos que dependem das atividades de agentes seguem o [roteiro separado](../../roteiro-agente.md). A execução observada é registrada em [validação](../../validacao.md).

## Passos de implementação

### SI03.1 — Publicar identidade verificável e sessão revogável

- Tipo: infraestrutura.
- Depende de: F01 disponível.
- Ações: Configurar credenciais de desenvolvimento, hash de senha, emissão e verificação JWT e registro de sessão no banco de identidade.
- Testes: Cobrir autenticação positiva e estados ausente, vencido, alterado e revogado com credenciais descartáveis.
- Critérios: F03-AC01, F03-AC02, F03-SEC02.

### SI03.2 — Integrar guard e encerrar sessão pelo navegador

- Tipo: comportamento.
- Depende de: SI03.1.
- Ações: Aplicar autorização aos consumidores, mapear dependência indisponível a erro sem efeito e conectar logout à sessão do servidor.
- Testes: Exercitar matriz por papel, falha controlada da introspecção e tentativa com a sessão após logout.
- Critérios: F03-AC03, F03-AC04, F03-SEC01.

### SI03.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para autenticação e autorização.
- Testes: Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas.
- Critérios: NFR01-AC01, NFR03-AC01.

## Execução observada dos passos

O plano descreve a decomposição esperada. A existência do código permite identificar implementação, mas não comprova execução histórica SI por SI. Os passos de Base têm implementação referenciada na spec e evidências anteriores em validação. Passos de Aula do agente e Avaliação acadêmica continuam pendentes. Revisão independente, aceite humano por critério e integração Git devem ser registrados antes do fechamento.
