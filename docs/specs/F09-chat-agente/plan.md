# Plano de implementação — F09 — Chat do morador e agente

## Dependências


## Passos de implementação

### SI09.1 — Concluir shell autenticado e limites de sessão

- Tipo: infraestrutura.
- Depende de: F02 e F03 disponíveis.
- Ações: Persistir ida e volta de sessão por unidade, checar titularidade e renderizar indisponibilidade observável sem um modelo.
- Testes: Abrir, recarregar e tentar acessar sessões com outros papéis e identidades.
- Critérios: F09-AC02, F09-AC05, F09-SEC01.

### SI09.2 — Praticar orquestração e ferramentas de consulta

- Tipo: comportamento.
- Depende de: SI09.1 e F06 a F08 de leitura.
- Ações: Compor três agentes com protocolo tipado: principal extrai DelegatedRequest com validação de tipos e chaves, o servidor projeta somente os campos pertinentes à operação, e o mapa fixo calcula o destino e cada especialista executa somente seu envelope do turno por uma ferramenta sem argumentos. Aplicar o escopo autorizado e consultar somente trecho pertinente do regulamento.
- Testes: Coletar eventos de delegação, transferência e executor, incluindo tentativa de troca de unidade, chamada direta fora do protocolo, envelope inválido/de outro turno, filho incorreto e nenhuma tool. Confirmar zero efeito e erro identificável nas falhas; somente resultado canônico autorizado na resposta e no histórico.
- Critérios: F09-AC01, F09-AC04.

### SI09.3 — Praticar confirmações e retomada persistida

- Tipo: comportamento.
- Depende de: SI09.2 e operações da integração em F07 e F08.
- Ações: Criar proposta idempotente vinculada ao turno no ledger existente, produzir cartão canônico e consumir a pendência original exclusivamente na rota de decisão humana. Preservar transação, recibo e histórico; não manter transação de banco durante geração nem repetir mutação para recuperar texto.
- Testes: Provar aprovação, recusa, reenvio 409, execução duplicada/paralela e recuperação depois de parar e iniciar o serviço. Na mesma sessão com recusas antigas, produzir pendência de visita e depois de reserva paga sem reutilizar intenção ou argumentos de outro turno.
- Critérios: F09-AC03.

### SI09.4 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para chat do morador e agente.
- Testes: solicitar GET /api/resident/chat/sessions/{QA_SESSION_A}/history com QA_B; confirmar que HTTP 404 SESSION_NOT_FOUND e nenhum texto ou pendência da sessão de QA_A; reiniciar agent sem restore, ler /history e decidir QA_PENDING com QA_A; reenviar a decisão; confirmar que histórico e pendência sobrevivem, primeira decisão válida produz um efeito e segunda retorna 409 sem duplicação; ler /history de QA_SESSION_A com QA_A após uma resposta e inspecionar o texto público; confirmar que retorna só mensagens e recibos autorizados; exclui texto de QA_B, instruções internas, payloads de tools, bearer e segredos.
- Critérios: NFR01-AC01, NFR02-AC01, NFR03-AC01.

### SI09.5 — Entregar conversa contínua e restaurar histórico na interface

- Tipo: comportamento.
- Depende de: SI09.1, SI09.2 e SI09.3.
- Ações: Retomar a sessão canônica por unidade, carregar o histórico sem seleção manual e apresentar a conversa em uma única linha do tempo fluida com compositor no rodapé. Preservar pendências, rascunhos e histórico autorizado.
- Testes: reiniciar agent sem restore, ler /history e decidir QA_PENDING com QA_A; reenviar a decisão; confirmar que histórico e pendência sobrevivem, primeira decisão válida produz um efeito e segunda retorna 409 sem duplicação.
- Critérios: F09-AC05, F09-AC06, F09-SEC01, NFR02-AC01.

### SI09.6 — Limitar histórico e admissão antes da execução externa

- Tipo: comportamento.
- Depende de: SI09.5 e SI01.8.
- Ações: tipar respostas e confirmações públicas; paginar projeção persistente com cursor e limite SQL; manter histórico disponível sem provedor; reservar admissão transacional por sessão, morador e global antes de Gemini; filtrar instruções internas da resposta pública.
- Testes: percorrer páginas sem lacunas/repetições e medir leitura limitada; concorrer pedidos e conferir recusa antes do provedor; abrir histórico e enviar mensagem com agente desligado; repetir cenários de privacidade e retomada de confirmação.
- Critérios: F09-AC03, F09-AC05, F09-AC06, F09-SEC01, NFR01-AC01, NFR02-AC01, NFR03-AC01.
