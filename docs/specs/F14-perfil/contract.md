# Contrato de verificação — F14 — Consulta do próprio perfil

## Pré-requisitos

Portal compilado, conta do perfil correto e massa descartável. Para autorização usar API real. Para disposição visual pode-se simular respostas sanitizadas.

## Itens

- **E2E-F14-01** (P0D, cobre F14-AC01) — Uma conta autenticada; selecionar o nome na barra superior -> a tela Meu perfil apresenta nome, e-mail e tipo da identidade autenticada. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F14-02** (P0D, cobre F14-AC02) — Sessão encerrada; tentar abrir a rota de perfil -> o portal volta à entrada e a API privada recusa a sessão revogada. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F14-03** (P0D, cobre F14-SEC01) — Tentar acesso direto sem a permissão exigida -> O perfil é obtido da identidade autenticada, sem aceitar um ID arbitrário da interface. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F14-04** (P0D, cobre NFR01-AC01) — Solicitar API da tela com identidade sem permissão -> Acesso recusado e nenhum dado protegido na resposta. Modo: API real em QA.

- **E2E-F14-05** (P0D, cobre NFR03-AC01) — Inspecionar projeções e evidência dos dois perfis -> Nenhum segredo ou dado de outra conta publicado. Modo: API real em QA.

## Cobertura

Cada item P0D corresponde ao critério funcional ou de segurança identificado no requisito e na matriz de testes da spec. Casos de privacidade e autorização usam as APIs reais com contas de papéis distintos.
