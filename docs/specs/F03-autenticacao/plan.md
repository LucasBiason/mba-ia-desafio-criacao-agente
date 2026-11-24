# Plano de implementação — F03 — Autenticação e autorização

## Dependências


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
- Testes: reutilizar esse bearer em GET /api/auth/me; confirmar que HTTP 401 INVALID_SESSION e ausência de perfil no corpo; executar POST /api/auth/login com senha inválida e GET /api/auth/me com a sessão válida; inspecionar corpos e logs sanitizados; confirmar que recusa 401 não repete a senha, perfil 200 exclui password_hash e logs não contêm senha nem token.
- Critérios: NFR01-AC01, NFR03-AC01.
