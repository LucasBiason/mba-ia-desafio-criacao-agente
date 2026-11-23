# Changelog

Todas as alterações relevantes deste projeto serão documentadas neste arquivo.
O formato segue Keep a Changelog e as versões seguem o versionamento semântico.

## [Unreleased]

### Added
- Ambiente Docker Compose com portal React, oito serviços por domínio e fronteira do agente, além de dois bancos PostgreSQL.
- Login, saída, consulta de perfil e gestão de contas dos tipos Administração e Morador.
- Cadastros administrativos de apartamentos e áreas, com vínculos de responsabilidade e preservação do histórico.
- Agenda mensal por área com busca por código, detalhes do dia e edição de horários de reservas e visitas.
- Regulamento versionado com autoria, publicação e recusa de edição sobre versão ultrapassada.
- Consultas do morador e sessões persistidas de chat, com integração do agente indicada como pendente.
- Navegação com ícones, menu compacto no desktop e diálogo acessível em telas pequenas.
- PRD, quatorze pacotes de especificação e documentação de arquitetura em docs/design/.
- Testes HTTP e de runtime para validar permissões e persistência.

### Changed

- Framework genérico organizado em submódulos, com lifespan de validação de secrets e infraestrutura ORM centralizados.
- Convenções e permissões do residencial isoladas no aurora-toolkit; serviço de configurações renomeado para parameters.
- Health definido como liveness e preparação de schema/fixtures movida para jobs explícitos, removendo a camada services/persistence e o upgrade legado.

- Toolkit reorganizado em factory por fases, router de health, autenticação e OpenAPI separados, com operações ORM transacionais e documentação pública no projeto da biblioteca.
- Diagnósticos estruturados por ambiente, logs de exceção correlacionados e remoção do README/lock redundantes do pacote incorporado.

- Testes próprios do toolkit mantidos em seu projeto de origem, sem duplicação no pacote embarcado.

- Recorte administrativo manual explicitado no PRD e nas specs, preservando os requisitos posteriores do desafio.
- Arquitetura consolidada com contexto, aplicações, modelo conceitual e ADRs rastreáveis.
- Makefile como interface operacional, entrypoint com comandos explícitos e Dockerfile com estágios de desenvolvimento e produção.
- Compose de desenvolvimento com recarga automática e preservação dos volumes existentes.
- Preparação local em configs/ e massa sintética em dados/, removendo a pasta scripts/ da raiz.
- Serviços separados por domínio com routers, controllers, validators, repositories SQLAlchemy e serializers.
- Health centralizado no toolkit e Swagger por serviço, mantendo os caminhos públicos do portal.
- Fundação HTTP compartilhada com microservice-toolkit, logs estruturados, correlação e autenticação configurável.
- Testes de integração localizados na aplicação de domínio e importador administrativo por API em dados/.
- Logo oficial do projeto aplicado ao login e aos menus do portal, incluindo o modo compacto e a navegação móvel.
- Enunciado preservado em docs/enunciado.md e README reorganizado com identidade visual e instruções de execução.

### Fixed

- Entradas de usuário e login com caractere nulo são recusadas na validação, preservando as senhas sem normalização implícita.

- Foco do teclado contido no menu móvel durante navegação com Tab e Shift+Tab, preservando Escape e seleção de página.

### Security
- Validação de JWT e autorização por papel e unidade nas APIs privadas.
- Proteção da última conta administrativa ativa, recusa de chamadas internas pelo proxy e bloqueio das APIs durante indisponibilidade da autenticação.
- Configuração local gerada fora do Git e preservação dos cinco arquivos de dados iniciais.

[Unreleased]: https://github.com/LucasBiason/mba-ia-desafio-criacao-agente/compare/main...feat/base-administrativa-limpa
