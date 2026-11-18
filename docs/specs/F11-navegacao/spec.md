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



O recorte de entrega vigente está no [PRD](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento). Casos identificados como integração do agente ou modo acadêmico permanecem especificados para a próxima etapa; não são condição de fechamento da administração manual. Sua ausência não significa aceite desses comportamentos.

## 2. Impacto arquitetural

O navegador resolve a rota, carrega a identidade e chama as APIs existentes na mesma origem. A autorização de dados permanece no servidor. A interface apresenta estado de carregamento e recusa sem revelar o conteúdo protegido.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

Reutilizar o Shell e os componentes Synapse presentes no produto. As decisões foram observadas em web/src/app.jsx; web/src/ui.jsx; web/src/styles/app.css. A navegação por hash conserva os caminhos existentes. Falha de identidade limpa a sessão do navegador e exige nova entrada.

O diálogo móvel contém a navegação de teclado entre seus elementos visíveis e habilitados: Tab no último retorna ao primeiro, e Shift+Tab no primeiro retorna ao último. Escape e clique externo fecham o menu; escolher uma página fecha e transfere foco ao conteúdo. A regressão em web/tests/test_mobile_navigation.py exercita os dois sentidos em 390 e 720 px.

## 4. Visão de componentes

Implementação em web/src/app.jsx; web/src/ui.jsx; web/src/styles/app.css. A API fornece identidade e dados de domínio, o React resolve as páginas e os componentes apresentam carregamento, conteúdo e erro. Os links preservam nomes acessíveis e o foco usa os componentes existentes.

## 5. Contratos de interface

Entrada pela navegação do portal no perfil correspondente. As chamadas existentes GET /api/auth/me e as projeções do domínio mantêm o bearer token. Uma recusa de sessão retorna 401. Dados de outro papel permanecem sujeitos ao guard. O resultado observável da UI está nos critérios do PRD.

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
| NFR01-AC01 | Enviar requisição sem token ou com papel indevido à API utilizada pela tela | O servidor recusa acesso e a interface apresenta a recusa sem dados protegidos. |
| NFR03-AC01 | Inspecionar a resposta e o conteúdo renderizado com identidades distintas | Tokens e dados de outras contas não aparecem na evidência publicada. |
