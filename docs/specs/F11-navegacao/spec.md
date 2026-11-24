---
spec_template: 1
feature: F11
ceremony: full
prd_source: docs/prd/functional/F11-navegacao.md
---

# F11 — Navegação responsiva por perfil

## 1. Visão técnica

Oferecer acesso aos caminhos autorizados por perfil, com barra lateral compacta no desktop e menu modal no celular.

A interface usa a identidade autenticada e as projeções do domínio, preservando os contratos existentes.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

O navegador resolve a rota, carrega a identidade e chama as APIs existentes na mesma origem. A autorização de dados permanece no servidor. A interface apresenta estado de carregamento e recusa sem revelar o conteúdo protegido.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

Reutilizar o Shell e os componentes Synapse presentes no produto. As decisões foram observadas em services/frontend/src/app.jsx; services/frontend/src/ui.jsx; services/frontend/src/styles/app.css. A navegação por hash conserva os caminhos existentes. Falha de identidade limpa a sessão do navegador e exige nova entrada.

O diálogo móvel contém a navegação de teclado entre seus elementos visíveis e habilitados: Tab no último retorna ao primeiro, e Shift+Tab no primeiro retorna ao último. Escape e clique externo fecham o menu; escolher uma página fecha e transfere foco ao conteúdo. A regressão em services/frontend/tests/test_mobile_navigation.py exercita os dois sentidos em 390 e 720 px.

## 4. Visão de componentes

Implementação em services/frontend/src/app.jsx; services/frontend/src/ui.jsx; services/frontend/src/styles/app.css. A API fornece identidade e dados de domínio, o React resolve as páginas e os componentes apresentam carregamento, conteúdo e erro. Os links preservam nomes acessíveis e o foco usa os componentes existentes.

## 5. Contratos de interface

A navegação consome GET `/api/auth/me` e mantém os guards das rotas de domínio. Como resident, abrir `#/admin/usuarios` não concede GET `/api/admin/users` (403); sem sessão, GET `/api/auth/me` retorna 401. Desktop 1280×900 e celular 390×844 exercitam nomes acessíveis, recolhimento, modal, Escape, toque externo e foco. Os requests privados usam Authorization bearer. Falha 503 conserva erro recuperável sem apresentar sucesso ou dados antigos como resposta nova. Os corpos de erro seguem o toolkit descrito em [F03](../F03-autenticacao/spec.md#5-contratos-de-interface).

## 6. Modelo de dados

A feature apresenta projeções e estado transitório da interface. Não cria tabelas. Nome, e-mail e papel vêm da identidade; contagens e registros vêm do domínio. Recarregar refaz a consulta sem alterar reservas, contas ou autorizações.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F11-AC01 | Um administrador ou morador autenticado; abrir seu portal | o menu mostra itens correspondentes ao perfil, ícones, nomes acessíveis e estado ativo. |
| F11-AC02 | Uma tela com pelo menos 721 px; recolher e expandir o menu | o espaço do conteúdo acompanha o menu e todos os links conservam nomes acessíveis. |
| F11-AC03 | Uma tela com até 720 px; abrir o menu, navegar, usar Escape ou tocar fora | o menu sobreposto fecha, permite navegação por teclado e não ocupa permanentemente o conteúdo. |
| F11-AC04 | Menu aberto em celular; navegar pelo teclado e selecionar uma rota | o foco fica no diálogo durante a interação e chega ao conteúdo após a seleção. |
| F11-SEC01 | Tentar acesso direto sem a permissão exigida | API mantém autorização mesmo se o cliente alterar o hash ou o HTML. |
| NFR01-AC01 | Portal e API reais. Dado QA_A é resident com menu do morador aberto; quando abrir #/admin/usuarios e solicitar GET /api/admin/users com o bearer QA_A. | Então API retorna 403 e nenhum usuário administrativo é exibido. |
| NFR03-AC01 | Portal e API reais. Dado QA_A e QA_ADMIN abrem os respectivos menus; quando inspecionar GET /api/auth/me e nomes acessíveis da navegação em cada sessão. | Então cada menu usa o papel da própria conta, sem senha, bearer ou perfil da outra sessão. |
