# Contrato de verificação — F13 — Visão geral do morador

## Pré-requisitos

Portal compilado, conta do perfil correto e massa descartável. Para autorização usar API real. Para disposição visual pode-se simular respostas sanitizadas.

## Itens

- **E2E-F13-01** (P0D, cobre F13-AC01) — Morador vinculado a uma unidade; abrir o portal e selecionar a unidade -> o resumo usa somente as reservas e visitas permitidas para essa identidade. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F13-02** (P0D, cobre F13-AC02) — Morador sem unidade vinculada; abrir a visão geral -> o estado vazio explica o vínculo necessário e não apresenta dados de terceiros. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F13-03** (P0D, cobre F13-SEC01) — Tentar acesso direto sem a permissão exigida -> Parâmetro de apartamento de outra conta é recusado pelo servidor. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F13-04** (P0D, cobre NFR01-AC01) — Solicitar API da tela com identidade sem permissão -> Acesso recusado e nenhum dado protegido na resposta. Modo: API real em QA.

- **E2E-F13-05** (P0D, cobre NFR03-AC01) — Inspecionar projeções e evidência dos dois perfis -> Nenhum segredo ou dado de outra conta publicado. Modo: API real em QA.

## Cobertura

Cada critério do requisito tem item P0D. A execução anterior e a revisão desta rodada estão registradas em [entrega](../../entrega-01.md). Aceite humano e integração Git aguardam registro.
