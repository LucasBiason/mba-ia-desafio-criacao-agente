---
spec_template: 1
feature: F13
ceremony: full
prd_source: docs/prd/functional/F13-painel-morador.md
---

# F13 — Visão geral do morador

## 1. Visão técnica

Mostrar ao morador o resumo de sua unidade selecionada e os caminhos para consultas e assistente.

A interface usa a identidade autenticada e as projeções do domínio, preservando os contratos existentes.



O [recorte de entrega](../../prd/index.md#recorte-de-entrega-e-critérios-de-fechamento) separa base administrativa, portal com assistente e API do assistente. Os modos dos critérios mantêm a superfície exigida; implementar não equivale a demonstrar o aceite.

## 2. Impacto arquitetural

O navegador resolve a rota, carrega a identidade e chama as APIs existentes na mesma origem. A autorização de dados permanece no servidor. A interface apresenta estado de carregamento e recusa sem revelar o conteúdo protegido.

## 3. Decisões técnicas

Decisões arquiteturais relacionadas: [ADR-0003](../../adr/ADR-0003-identidade-central-e-autorizacao-por-recurso.md).

Reutilizar o Shell e os componentes Synapse presentes no produto. As decisões foram observadas em services/frontend/src/resident.jsx; services/apartments/main.py. A navegação por hash conserva os caminhos existentes. Falha de identidade limpa a sessão do navegador e exige nova entrada.

## 4. Visão de componentes

Implementação em services/frontend/src/resident.jsx; services/apartments/main.py. A API fornece identidade e dados de domínio, o React resolve as páginas e os componentes apresentam carregamento, conteúdo e erro. Os links preservam nomes acessíveis e o foco usa os componentes existentes.

## 5. Contratos de interface

O painel `#/inicio` de resident consome GET `/api/resident/apartments` e, após selecionar 9101, GET `/api/resident/reservations?apartment=9101` e `/api/resident/visits?apartment=9101`. Sem vínculo apresenta estado vazio e não consulta outra unidade. Usar 9102 de QA_B com QA_A retorna 403. Sem bearer, 401. Os requests privados usam Authorization bearer. Falha 503 conserva erro recuperável sem apresentar sucesso ou dados antigos como resposta nova. Os corpos de erro seguem o toolkit descrito em [F03](../F03-autenticacao/spec.md#5-contratos-de-interface).

## 6. Modelo de dados

A feature apresenta projeções e estado transitório da interface. Não cria tabelas. Nome, e-mail e papel vêm da identidade; contagens e registros vêm do domínio. Recarregar refaz a consulta sem alterar reservas, contas ou autorizações.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F13-AC01 | Morador vinculado a uma unidade; abrir o portal e selecionar a unidade | o resumo usa somente as reservas e visitas permitidas para essa identidade. |
| F13-AC02 | Morador sem unidade vinculada; abrir a visão geral | o estado vazio explica o vínculo necessário e não apresenta dados de terceiros. |
| F13-SEC01 | Tentar acesso direto sem a permissão exigida | Parâmetro de apartamento de outra conta é recusado pelo servidor. |
| NFR01-AC01 | Portal e API reais. Dado QA_A só está vinculado a 9101; quando solicitar GET /api/resident/reservations?apartment=9102 e GET /api/resident/visits?apartment=9102 com QA_A. | Então ambas retornam 403 e o painel não apresenta dados de 9102. |
| NFR03-AC01 | Portal e API reais. Dado 9101 tem QA_RES_A e 9102 tem QA_RES_B; quando abrir #/inicio como QA_A, selecionar 9101 e inspecionar respostas de reservas e visitas. | Então resumo contém somente registros de QA_A/9101, sem QA_RES_B, nomes alheios ou credenciais. |
