# Primeira entrega — base administrativa e portal

## Alcance e situação

A base foi integrada ao checkout do fork LucasBiason/mba-ia-desafio-criacao-agente na branch local feat/base-administrativa. O README com identidade visual, os assets e o enunciado foram preservados. O catálogo F01–F14 consolida os requisitos e docs/prd mantém os ponteiros dos identificadores anteriores. A cópia integral anterior à integração foi conservada fora do checkout para recuperação.

As telas administrativas entregam usuários, apartamentos, áreas, agenda, visitas e regulamento. Agenda e visitas permitem registrar horários de registros existentes. O morador dispõe de consultas próprias e sessão de chat persistida. O serviço de agente responde AGENT_NOT_CONFIGURED. Criação e cancelamento por ferramentas, confirmação, consulta ao regulamento pelo modelo e avaliação acadêmica continuam no roteiro guiado.

## Matriz de funcionalidades

| ID | Situação | Recorte desta PR | Evidência e pendência |
| --- | --- | --- | --- |
| F01 | Implementada; aceite de entrega pendente | Compose, proxy, PostgreSQL e carga inicial | tests/test_runtime.py e registro de validação |
| F02 | Implementada; aceite de entrega pendente | Código e número de unidade, responsável único, histórico preservado | tests/test_api.py — contas, apartamentos e importação |
| F03 | Implementada com verificações residuais | Login, JWT, autorização, saída e recusa em indisponibilidade | tests/test_api.py; tests/test_runtime.py; expiração controlada permanece pendente |
| F04 | Implementada; aceite de entrega pendente | Tipos Administração e Morador; cadastro, edição e ativação; proteção da última administração | tests/test_api.py — contas e última administração |
| F05 | Implementada; aceite de entrega pendente | Cadastro e taxa de áreas, edição e exclusão protegida | tests/test_api.py — áreas e agenda |
| F06 | Implementada; aceite de entrega pendente | Regulamento vigente, edição, histórico e conflito de versão | tests/test_api.py — versões; validação prévia de concorrência |
| F07 | Parcial | Agenda mensal, filtros, busca por código, painel do dia e horários; consulta própria | Validação prévia HTTP e Chromium; criação, cancelamento e confirmação pelo agente pendentes |
| F08 | Parcial | Consulta por papel e registro de entrada e saída | tests/test_api.py — horários e escopo; novas autorizações confirmadas pendentes |
| F09 | Parcial | Sessão persistida, seleção de unidade e indicação de indisponibilidade do agente | tests/test_api.py — sessão e histórico; ADK, tools, eventos e confirmação pendentes |
| F10 | Pendente | Especificação da futura API de avaliação | Sem execução dos 15 passos. Adaptador acadêmico e agente são dependências |
| F11 | Implementada; aceite de entrega pendente | Oferecer acesso aos caminhos autorizados por perfil, com barra lateral compacta no desktop e menu modal no celular. | Navegação anterior em Chromium com respostas simuladas; autorização conforme evidências HTTP da base |
| F12 | Implementada; aceite de entrega pendente | Consolidar os totais de cadastros e os atalhos de gestão para iniciar a operação administrativa. | Navegação anterior em Chromium com respostas simuladas; autorização conforme evidências HTTP da base |
| F13 | Implementada; aceite de entrega pendente | Mostrar ao morador o resumo de sua unidade selecionada e os caminhos para consultas e assistente. | Navegação anterior em Chromium com respostas simuladas; autorização conforme evidências HTTP da base |
| F14 | Implementada; aceite de entrega pendente | Permitir que cada conta confira nome, e-mail e tipo associados à sessão corrente. | Navegação anterior em Chromium com respostas simuladas; autorização conforme evidências HTTP da base |


## Histórico SDD verificável

Foram encontrados spec.md, plan.md e contract.md de F01 a F10. Os arquivos vinculam critérios do PRD aos passos e às provas esperadas. O registro de validação relata execução de nove testes HTTP, provas de persistência e jornadas em Chromium. Não foram encontrados laudos individuais que permitam afirmar que cada feature passou pela sequência das três skills ou por auditor independente. Esta revisão acrescenta os pacotes de F11 a F14 e explicita a situação nos demais. Uma spec retrospectiva descreve o sistema observado e preserva a distinção entre teste proposto e resultado executado.

A aprovação visual do usuário reconhece a base das telas. Aceite integral de todos os critérios, integração Git e merge ainda precisam de registro. F07, F08 e F09 permanecem parciais. F10 permanece pendente.

## Evidências e limites

- A [validação anterior](validacao.md) relata operações HTTP em ambiente QA e navegação real com dados descartáveis.
- A revisão de menu verificou no Chromium os dois perfis em 1440, 721, 390 e 320 px, com respostas de API simuladas. Essa prova cobre UI e foco. As garantias de autorização dependem das provas HTTP.
- O calendário preserva seu componente genérico em web/src/calendar.jsx e web/src/styles/calendar.css; a integração de domínio fica em agenda.jsx e agenda.css.
- Os dados sintéticos da agenda pertencem ao ambiente local. A primeira PR leva o gerador e os arquivos iniciais; volumes e conteúdo local da carga não entram no Git.
- A expiração controlada de token e cenários residuais do contrato de autenticação seguem sem nova prova nesta rodada.
- A revisão documental executa os validadores canônicos do MiniBrain sobre todos os pacotes. Um resultado estrutural não equivale ao aceite funcional.

## Fechamento da primeira pull request

1. Integração local concluída em feat/base-administrativa. Os arquivos iniciais foram comparados com HEAD; identidade visual e enunciado foram preservados.
2. Fonte, lockfiles, Compose, testes e documentação integrados seletivamente. Arquivos de configuração local, credenciais, caches, dependências instaladas e volumes ficaram fora do manifesto candidato.
3. Repetir build e nove testes de API em uma composição descartável criada a partir da branch candidata. Executar os testes de runtime e as jornadas essenciais dos dois perfis. Resolver a prova residual de autenticação ou registrar seu impedimento de aceite.
4. Produzir avaliação independente e revisão do diff com evidência por critério do recorte Base. Marcar os critérios do agente explicitamente como etapa posterior. Submeter o pacote ao usuário.
5. Publicar commit, branch e PR somente no fork LucasBiason/mba-ia-desafio-criacao-agente mediante autorização de publicação. Conferir remote de push imediatamente antes da operação. Registrar URL e resultado da integração.

## Rascunho de descrição da PR

Título proposto: feat: entrega base administrativa e portal do Residencial Aurora

Esta entrega disponibiliza a composição local com identidade e permissões, cadastros administrativos, agenda mensal, registros de horários, regulamento versionado e consultas do morador. O portal usa React e Synapse, com navegação responsiva e sessão persistida de chat.

A consultoria com Google ADK e Gemini será construída na jornada guiada. O endpoint de mensagem sinaliza indisponibilidade enquanto essa etapa está pendente. O adaptador local da avaliação acadêmica e seus 15 passos pertencem à etapa seguinte.

Antes de publicar, acrescentar os resultados da avaliação da branch candidata, o roteiro reproduzido e os limites confirmados da revisão. O registro anterior de validação serve como evidência da base isolada.

## Resultado desta revisão documental

- O validador canônico validate_prd.py aprovou a árvore de 14 funcionalidades e quatro NFRs.
- O lint_spec.py com --strict e --require-template aprovou os 14 pacotes de spec, plano e contrato.
- A inspeção de links locais da documentação não encontrou destinos ausentes.
- Nesta rodada, a inspeção do Compose confirmou sete serviços em execução na base de uso.
- O MiniBrain canônico foi consultado na árvore de trabalho, que contém mudanças locais; a referência Git observada é f926b0e. Os validadores usados são os arquivos atuais dessa árvore.
- Não houve nova execução da suíte HTTP com mutações ou dos testes de reinício nesta revisão documental. As provas anteriores continuam no registro de validação com esse alcance.


## Validação da branch integrada

- Build completo dos serviços e frontend pelo Compose em projeto novo aurora-fork-pr1-20261117.
- uv sync --locked concluído.
- Nove testes HTTP de tests/test_api.py aprovados pela origem 127.0.0.1:8768.
- tests/test_runtime.py aprovado: indisponibilidade da autenticação resulta em 503 e o reinício integral preserva contas, vínculos, versões, agenda, visitas e sessões.
- O teste de runtime aceita COMPOSE_PROJECT_NAME para validar uma composição isolada, conservando a verificação da porta de QA.
- PRD e 14 pacotes de spec, plano e contrato aprovados pelos validadores canônicos.
- Git diff --check aprovado e os cinco arquivos de dados permanecem idênticos ao HEAD.
- Varredura dos arquivos candidatos confirmou ausência dos segredos gerados pelo ambiente de QA e ausência de .env, caches, node_modules e dist.
- O projeto de QA antigo tinha volumes com configuração diferente. A branch foi validada em volumes novos; a instância de uso em 8767 permaneceu disponível.
- O Compose da branch de QA atende em 127.0.0.1:8768. Publicação autorizada pelo usuário, com commits por fase e tag v0.1.0. PR #1 criada no fork LucasBiason. Tag v0.1.0 atribuída ao commit final do pacote, com merge pendente.

- Chromium com API real da branch: login, todas as rotas administrativas e de morador, perfil e logout aprovados em 1440 e 390 px. Busca de RSV-4821 e fechamento dos detalhes da agenda aprovados nos dois tamanhos. Nenhuma exceção JavaScript ou transbordamento horizontal observado. O assistente mantém o aviso esperado de integração pendente.


## Publicação pela sdd-delivery

[PR #1](https://github.com/LucasBiason/mba-ia-desafio-criacao-agente/pull/1) aberta da branch feat/base-administrativa para main do fork LucasBiason. A entrega usa a versão 0.1.0 e tag anotada v0.1.0. A tag identifica o pacote submetido à revisão; o merge segue pendente.

Os arquivos foram selecionados explicitamente por fase antes de cada commit. As verificações incluíram padrões de credenciais e JWTs, chaves privadas, caminhos pessoais, exclusões de configuração local e integridade dos dados iniciais. Não foram detectadas ocorrências nos candidatos. A varredura por padrões tem limites e não equivale a auditoria independente.

Os quatro commits de conteúdo separam infraestrutura, API, interface e documentação. O commit posterior registra a publicação. Autor e committer usam exclusivamente a identidade de Lucas Biason configurada no Git; as mensagens não têm trailer de coautoria.

O changelog segue Keep a Changelog, com Unreleased e 0.1.0, e a descrição da PR apresenta escopo, testes executados, referências e pendências. A skill foi aplicada pela leitura das instruções canônicas e execução dos comandos verificados. Não existe evidência de uma avaliação independente sdd-evaluate por item nesta entrega. Os critérios do agente e da avaliação acadêmica permanecem pendentes.
