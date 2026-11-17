# Changelog

Todas as alterações relevantes deste projeto serão documentadas neste arquivo.
O formato segue Keep a Changelog e as versões seguem o versionamento semântico.

## [Unreleased]

## [0.1.0] - 2026-11-17

### Added

- Ambiente Docker Compose com portal React, serviços de autenticação, usuários, condomínio e fronteira do agente, além de dois bancos PostgreSQL.
- Login, saída, consulta de perfil e gestão de contas dos tipos Administração e Morador.
- Cadastros administrativos de apartamentos e áreas, com vínculos de responsabilidade e preservação do histórico.
- Agenda mensal por área com busca por código, detalhes do dia e edição de horários de reservas e visitas.
- Regulamento versionado com autoria, publicação e recusa de edição sobre versão ultrapassada.
- Consultas do morador e sessões persistidas de chat, com integração do agente indicada como pendente.
- Navegação com ícones, menu compacto no desktop e diálogo acessível em telas pequenas.
- PRD, quatorze pacotes de especificação e roteiro guiado da integração Google ADK/Gemini.
- Testes HTTP e de runtime para validar permissões e persistência.

### Changed

- Enunciado preservado em docs/enunciado.md e README reorganizado com identidade visual e instruções de execução.

### Security

- Validação de JWT e autorização por papel e unidade nas APIs privadas.
- Proteção da última conta administrativa ativa, recusa de chamadas internas pelo proxy e bloqueio das APIs durante indisponibilidade da autenticação.
- Configuração local gerada fora do Git e preservação dos cinco arquivos de dados iniciais.

[Unreleased]: https://github.com/LucasBiason/mba-ia-desafio-criacao-agente/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/LucasBiason/mba-ia-desafio-criacao-agente/releases/tag/v0.1.0
