# Contrato de verificação — F12 — Visão geral administrativa

## Pré-requisitos

Portal compilado, conta do perfil correto e massa descartável. Para autorização usar API real. Para disposição visual pode-se simular respostas sanitizadas.

## Itens

- **E2E-F12-01** (P0D, cobre F12-AC01) — Uma conta administrativa e dados carregados; abrir a visão geral -> o painel mostra totais de apartamentos, áreas e reservas coerentes com as APIs. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F12-02** (P0D, cobre F12-AC02) — Painel administrativo aberto; selecionar um atalho de cadastro ou agenda -> a rota correspondente abre e o menu identifica o destino ativo. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F12-03** (P0D, cobre F12-SEC01) — Tentar acesso direto sem a permissão exigida -> Morador não obtém os dados administrativos ao solicitar diretamente suas APIs. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F12-04** (P0D, cobre NFR01-AC01) — Solicitar API da tela com identidade sem permissão -> Acesso recusado e nenhum dado protegido na resposta. Modo: API real em QA.

- **E2E-F12-05** (P0D, cobre NFR03-AC01) — Inspecionar projeções e evidência dos dois perfis -> Nenhum segredo ou dado de outra conta publicado. Modo: API real em QA.

## Cobertura

Cada item P0D corresponde ao critério funcional ou de segurança identificado no requisito e na matriz de testes da spec. Casos de privacidade e autorização usam as APIs reais com contas de papéis distintos.
