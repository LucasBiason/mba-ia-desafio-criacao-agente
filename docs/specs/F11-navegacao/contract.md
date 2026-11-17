# Contrato de verificação — F11 — Navegação responsiva por perfil

## Pré-requisitos

Portal compilado, conta do perfil correto e massa descartável. Para autorização usar API real. Para disposição visual pode-se simular respostas sanitizadas.

## Itens

- **E2E-F11-01** (P0D, cobre F11-AC01) — Um administrador ou morador autenticado; abrir seu portal -> o menu mostra itens correspondentes ao perfil, ícones, nomes acessíveis e estado ativo. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-02** (P0D, cobre F11-AC02) — Uma tela com pelo menos 721 px; recolher e expandir o menu -> o espaço do conteúdo acompanha o menu e todos os links conservam nomes acessíveis. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-03** (P0D, cobre F11-AC03) — Uma tela com até 720 px; abrir o menu, navegar, usar Escape ou tocar fora -> o menu sobreposto fecha, permite navegação por teclado e não ocupa permanentemente o conteúdo. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-04** (P0D, cobre F11-AC04) — Menu aberto em celular; navegar pelo teclado e selecionar uma rota -> o foco fica no diálogo durante a interação e chega ao conteúdo após a seleção. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-05** (P0D, cobre F11-SEC01) — Tentar acesso direto sem a permissão exigida -> API mantém autorização mesmo se o cliente alterar o hash ou o HTML. Modo: verificar API e navegação nos perfis e tamanhos correspondentes.

- **E2E-F11-06** (P0D, cobre NFR01-AC01) — Solicitar API da tela com identidade sem permissão -> Acesso recusado e nenhum dado protegido na resposta. Modo: API real em QA.

- **E2E-F11-07** (P0D, cobre NFR03-AC01) — Inspecionar projeções e evidência dos dois perfis -> Nenhum segredo ou dado de outra conta publicado. Modo: API real em QA.

## Cobertura

Cada critério do requisito tem item P0D. A execução anterior e a revisão desta rodada estão registradas em [entrega](../../entrega-01.md). Aceite humano e integração Git aguardam registro.
