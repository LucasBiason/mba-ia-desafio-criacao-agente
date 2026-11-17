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

## 2. Impacto arquitetural

O navegador resolve a rota, carrega a identidade e chama as APIs existentes na mesma origem. A autorização de dados permanece no servidor. A interface apresenta estado de carregamento e recusa sem revelar o conteúdo protegido.

## 3. Decisões técnicas

Reutilizar o Shell e os componentes Synapse presentes no produto. As decisões foram observadas em web/src/resident.jsx; services/apartments/main.py. A navegação por hash conserva os caminhos existentes. Falha de identidade limpa a sessão do navegador e exige nova entrada.

## 4. Visão de componentes

Implementação em web/src/resident.jsx; services/apartments/main.py. A API fornece identidade e dados de domínio, o React resolve as páginas e os componentes apresentam carregamento, conteúdo e erro. Os links preservam nomes acessíveis e o foco usa os componentes existentes.

## 5. Contratos de interface

Entrada pela navegação do portal no perfil correspondente. As chamadas existentes GET /api/auth/me e as projeções do domínio mantêm o bearer token. Uma recusa de sessão retorna 401. Dados de outro papel permanecem sujeitos ao guard. O resultado observável da UI está nos critérios do PRD.

## 6. Modelo de dados

A feature apresenta projeções e estado transitório da interface. Não cria tabelas. Nome, e-mail e papel vêm da identidade; contagens e registros vêm do domínio. Recarregar refaz a consulta sem alterar reservas, contas ou autorizações.

## 7. Estratégia de testes


| Critério | Teste | Evidência esperada |
| --- | --- | --- |
| F13-AC01 | Morador vinculado a uma unidade; abrir o portal e selecionar a unidade | o resumo usa somente as reservas e visitas permitidas para essa identidade. |
| F13-AC02 | Morador sem unidade vinculada; abrir a visão geral | o estado vazio explica o vínculo necessário e não apresenta dados de terceiros. |
| F13-SEC01 | Tentar acesso direto sem a permissão exigida | Parâmetro de apartamento de outra conta é recusado pelo servidor. |
| NFR01-AC01 | Enviar requisição sem token ou com papel indevido à API utilizada pela tela | O servidor recusa acesso e a interface apresenta a recusa sem dados protegidos. |
| NFR03-AC01 | Inspecionar a resposta e o conteúdo renderizado com identidades distintas | Tokens e dados de outras contas não aparecem na evidência publicada. |
