---
spec_template: 1
feature: F14
ceremony: full
prd_source: docs/prd/functional/F14-perfil.md
---

# F14 — Consulta do próprio perfil

## 1. Visão técnica

Permitir que cada conta confira nome, e-mail e tipo associados à sessão corrente.

A interface usa a identidade autenticada e as projeções do domínio, preservando os contratos existentes.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

O navegador resolve a rota, carrega a identidade e chama as APIs existentes na mesma origem. A autorização de dados permanece no servidor. A interface apresenta estado de carregamento e recusa sem revelar o conteúdo protegido.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

Reutilizar o Shell e os componentes Synapse presentes no produto. As decisões foram observadas em services/frontend/src/app.jsx; services/authentication/routers/authentication_router.py. A navegação por hash conserva os caminhos existentes. Falha de identidade limpa a sessão do navegador e exige nova entrada.

## 4. Visão de componentes

Implementação em services/frontend/src/app.jsx; services/authentication/routers/authentication_router.py. A API fornece identidade e dados de domínio, o React resolve as páginas e os componentes apresentam carregamento, conteúdo e erro. Os links preservam nomes acessíveis e o foco usa os componentes existentes.

## 5. Contratos de interface

A tela `#/perfil` é aberta pelo nome da conta e consome GET `/api/auth/me`; não recebe ID de usuário arbitrário. A resposta pública tem `id`, `name`, `email`, `role` e `active`, sem segredo derivado. POST `/api/auth/logout` revoga a sessão e responde 204; reutilizá-la em /me retorna 401 e a UI volta à entrada. Os requests privados usam Authorization bearer. Falha 503 conserva erro recuperável sem apresentar sucesso ou dados antigos como resposta nova. Os corpos de erro seguem o toolkit descrito em [F03](../F03-autenticacao/spec.md#5-contratos-de-interface).

A tela não disputa unicidade nem grava dados: não inicia transação de escrita e uma falha de leitura não exige rollback de domínio. Se logout ou revogação concorre com a leitura, a próxima consulta autoritativa recusa o bearer e a UI remove o perfil da sessão. Não há valor de credencial derivado exposto ao cliente.

## 6. Modelo de dados

A feature apresenta projeções e estado transitório da interface. Não cria tabelas. Nome, e-mail e papel vêm da identidade; contagens e registros vêm do domínio. Recarregar refaz a consulta sem alterar reservas, contas ou autorizações.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F14-AC01 | Uma conta autenticada; selecionar o nome na barra superior | a tela Meu perfil apresenta nome, e-mail e tipo da identidade autenticada. |
| F14-AC02 | Sessão encerrada; tentar abrir a rota de perfil | o portal volta à entrada e a API privada recusa a sessão revogada. |
| F14-SEC01 | Tentar acesso direto sem a permissão exigida | O perfil é obtido da identidade autenticada, sem aceitar um ID arbitrário da interface. |
| NFR01-AC01 | Portal e API reais. Dado A sessão QA_A foi revogada por POST /api/auth/logout; quando reutilizar o bearer revogado em GET /api/auth/me e abrir #/perfil. | Então API retorna 401 INVALID_SESSION e o portal retorna à entrada sem perfil. |
| NFR03-AC01 | Portal e API reais. Dado QA_A e QA_ADMIN estão autenticados em contextos de navegador separados; quando consultar GET /api/auth/me e abrir #/perfil em cada contexto. | Então nome, email e papel coincidem com a própria identidade; respostas excluem password_hash e dados da outra conta. |
