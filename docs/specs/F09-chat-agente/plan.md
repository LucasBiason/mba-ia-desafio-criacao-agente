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
- Ações: Selecionar uma topologia, fazer uma consulta de reserva pela tool, aplicar o escopo da sessão e consultar somente trecho do regulamento.
- Testes: Coletar eventos de transferência, chamada da tool e resposta, incluindo tentativa de troca de unidade.
- Critérios: F09-AC01, F09-AC04.

### SI09.3 — Praticar confirmações e retomada persistida

- Tipo: comportamento.
- Depende de: SI09.2 e operações da integração em F07 e F08.
- Ações: Ligar a execução suspensa à decisão externa, gravar eventos e retomar com o contexto correto do especialista.
- Testes: Provar aprovação, recusa, reenvio e recuperação depois de parar e iniciar o serviço.
- Critérios: F09-AC03.

### SI09.4 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para chat do morador e agente.
- Testes: Selecionar o caso negativo aplicável ao requisito e comparar status, estado e evidência observável. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita. Inspecionar projeções, eventos aplicáveis e registros sanitizados do caso sem publicar bearer, senha ou dados de outras contas.
- Critérios: NFR01-AC01, NFR02-AC01, NFR03-AC01.
