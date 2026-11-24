# Plano de implementação — F06 — Regulamento único e versionado

## Dependências


## Passos de implementação

### SI06.1 — Registrar versões e impedir edição concorrente

- Tipo: infraestrutura.
- Depende de: F03 disponível.
- Ações: Importar versão zero, criar armazenamento imutável e publicar sob comparação com versão-base.
- Testes: Publicar uma edição, repetir com base antiga e consultar histórico antes e depois do reinício.
- Critérios: F06-AC01, F06-AC02, F06-AC04.

### SI06.2 — Conectar editor, histórico e leitura vigente

- Tipo: comportamento.
- Depende de: SI06.1.
- Ações: Implementar telas por papel e tratar conteúdo editado como texto, incluindo recuperação do conflito.
- Testes: Exercitar edição admin, leitura residente e bloqueio à escrita e histórico por morador.
- Critérios: F06-AC03, F06-SEC01.

### SI06.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para regulamento único e versionado.
- Testes: publicar um texto sintético novo em PUT /api/admin/regulation com base_version=V; reiniciar parameters e ler vigente e /versions; confirmar que vigente permanece V+1 e histórico conserva V e V+1 com o texto e autor publicados; consultar GET /api/resident/regulation e GET /api/admin/regulation/versions usando QA_A; confirmar que vigente retorna 200 sem credenciais; histórico administrativo retorna 403 sem revisões de autoria alheia.
- Critérios: NFR02-AC01, NFR03-AC01.
