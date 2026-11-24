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



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

O navegador resolve a rota, carrega a identidade e chama as APIs existentes na mesma origem. A autorização de dados permanece no servidor. A interface apresenta estado de carregamento e recusa sem revelar o conteúdo protegido.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

Reutilizar o Shell e os componentes Synapse presentes no produto. A implementação está em AdminHome, em services/frontend/src/admin.jsx; a obtenção de dados usa useQuery, em services/frontend/src/api.js. A navegação por hash conserva os caminhos existentes. Falha de identidade limpa a sessão do navegador e exige nova entrada.

## 4. Visão de componentes

AdminHome consulta GET /api/admin/apartments, GET /api/admin/areas e GET /api/admin/reservations independentemente. Cada cartão apresenta carregamento, erro ou quantidade da projeção recebida; não há endpoint agregado nem escrita a partir do painel. A API fornece identidade e dados de domínio, o React resolve as páginas e os componentes apresentam carregamento, conteúdo e erro. Os links preservam nomes acessíveis e o foco usa os componentes existentes.

## 5. Contratos de interface

O painel `#/inicio` de admin consome GET `/api/admin/apartments`, `/api/admin/areas` e `/api/admin/reservations`. Os totais são os comprimentos das projeções autorizadas, sem endpoint agregador adicional. Os atalhos abrem `#/admin/apartamentos`, `#/admin/areas` e `#/admin/reservas`. Resident nessas APIs recebe 403; sem bearer, 401. Os requests privados usam Authorization bearer. Falha 503 conserva erro recuperável sem apresentar sucesso ou dados antigos como resposta nova. Os corpos de erro seguem o toolkit descrito em [F03](../F03-autenticacao/spec.md#5-contratos-de-interface).

## 6. Modelo de dados

A feature apresenta projeções e estado transitório da interface. Não cria tabelas. Nome, e-mail e papel vêm da identidade; contagens e registros vêm do domínio. Recarregar refaz a consulta sem alterar reservas, contas ou autorizações.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F12-AC01 | Uma conta administrativa e dados carregados; abrir a visão geral | o painel mostra totais de apartamentos, áreas e reservas coerentes com as APIs. |
| F12-AC02 | Painel administrativo aberto; selecionar um atalho de cadastro ou agenda | a rota correspondente abre e o menu identifica o destino ativo. |
| F12-SEC01 | Tentar acesso direto sem a permissão exigida | Morador não obtém os dados administrativos ao solicitar diretamente suas APIs. |
| NFR01-AC01 | Portal e API reais. Dado QA_A é resident; quando solicitar GET /api/admin/apartments, /api/admin/areas e /api/admin/reservations com QA_A. | Então as três chamadas retornam 403 sem totais ou registros administrativos. |
| NFR03-AC01 | Portal e API reais. Dado QA_ADMIN tem o painel aberto com massa sintética; quando comparar cards com GET /api/admin/apartments, /api/admin/areas e /api/admin/reservations e inspecionar os corpos. | Então contagens coincidem e nenhuma projeção contém senha, hash ou bearer. |
