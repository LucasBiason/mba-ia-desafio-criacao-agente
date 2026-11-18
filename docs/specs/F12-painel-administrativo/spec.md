---
spec_template: 1
feature: F12
ceremony: full
prd_source: docs/prd/functional/F12-painel-administrativo.md
---

# F12 — Visão geral administrativa

## 1. Visão técnica

Consolidar os totais de cadastros e os atalhos de gestão para iniciar a operação administrativa.

A interface usa a identidade autenticada e as projeções do domínio, preservando os contratos existentes.



O recorte de entrega vigente está no [PRD](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento). Casos identificados como integração do agente ou modo acadêmico permanecem especificados para a próxima etapa; não são condição de fechamento da administração manual. Sua ausência não significa aceite desses comportamentos.

## 2. Impacto arquitetural

O navegador resolve a rota, carrega a identidade e chama as APIs existentes na mesma origem. A autorização de dados permanece no servidor. A interface apresenta estado de carregamento e recusa sem revelar o conteúdo protegido.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

Reutilizar o Shell e os componentes Synapse presentes no produto. A implementação está em AdminHome, em web/src/admin.jsx; a obtenção de dados usa useQuery, em web/src/api.js. A navegação por hash conserva os caminhos existentes. Falha de identidade limpa a sessão do navegador e exige nova entrada.

## 4. Visão de componentes

AdminHome consulta GET /api/admin/apartments, GET /api/admin/areas e GET /api/admin/reservations independentemente. Cada cartão apresenta carregamento, erro ou quantidade da projeção recebida; não há endpoint agregado nem escrita a partir do painel. A API fornece identidade e dados de domínio, o React resolve as páginas e os componentes apresentam carregamento, conteúdo e erro. Os links preservam nomes acessíveis e o foco usa os componentes existentes.

## 5. Contratos de interface

Entrada pela navegação do portal no perfil correspondente. As chamadas existentes GET /api/auth/me e as projeções do domínio mantêm o bearer token. Uma recusa de sessão retorna 401. Dados de outro papel permanecem sujeitos ao guard. O resultado observável da UI está nos critérios do PRD.

## 6. Modelo de dados

A feature apresenta projeções e estado transitório da interface. Não cria tabelas. Nome, e-mail e papel vêm da identidade; contagens e registros vêm do domínio. Recarregar refaz a consulta sem alterar reservas, contas ou autorizações.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F12-AC01 | Uma conta administrativa e dados carregados; abrir a visão geral | o painel mostra totais de apartamentos, áreas e reservas coerentes com as APIs. |
| F12-AC02 | Painel administrativo aberto; selecionar um atalho de cadastro ou agenda | a rota correspondente abre e o menu identifica o destino ativo. |
| F12-SEC01 | Tentar acesso direto sem a permissão exigida | Morador não obtém os dados administrativos ao solicitar diretamente suas APIs. |
| NFR01-AC01 | Enviar requisição sem token ou com papel indevido à API utilizada pela tela | O servidor recusa acesso e a interface apresenta a recusa sem dados protegidos. |
| NFR03-AC01 | Inspecionar a resposta e o conteúdo renderizado com identidades distintas | Tokens e dados de outras contas não aparecem na evidência publicada. |
