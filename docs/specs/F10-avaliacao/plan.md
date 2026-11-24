# Plano de implementação — F10 — Compatibilidade e aceite do desafio

## Dependências


## Passos de implementação

### SI10.1 — Preservar fixtures e isolamento da composição base

- Tipo: infraestrutura.
- Depende de: F01 disponível.
- Ações: Auditar os dados originais e manter o namespace de produto protegido no proxy.
- Testes: Conferir hashes da origem e verificar que os caminhos do assistente e internos não são publicados.
- Critérios: F10-AC02, F10-AC04.

### SI10.2 — Implementar e provar o adaptador da API do assistente na integração

- Tipo: comportamento.
- Depende de: SI10.1 e F09 com as tools e confirmações concluídas.
- Ações: Fixar dependências, criar ponto de entrada e restauração isolados, expor o formato previsto e registrar as provas das garantias.
- Testes: Executar e registrar os 15 passos em clone limpo sem alterar as fixtures ou a instalação de produto.
- Critérios: F10-AC01, F10-AC03, F10-SEC01.

### SI10.3 — Verificar requisitos transversais

- Tipo: comportamento.
- Depende de: operações descritas nos passos anteriores na etapa de cada critério.
- Ações: preparar massa descartável e localizar as fronteiras que fornecem a prova para compatibilidade e aceite do desafio.
- Testes: enviar texto sim em /sessoes/{QA_SESSION}/mensagens sem chamar /confirmacoes e consultar /apartamentos/101/reservas; confirmar que a ação permanece pendente e nenhuma reserva paga nova existe; somente decisão externa válida poderá liberá-la; pedir nomes de visitantes de 202 pela sessão 101 e inspecionar resposta, eventos e projeção de 101; confirmar que tools mantêm apartamento 101 e a resposta não revela nome de 202 ou segredos; eventos de execução não contêm credenciais; criar QA_SESSION via POST /sessoes, enviar consulta e ler eventos via gateway; reiniciar uma réplica sem restore e reler eventos; confirmar que as seis rotas estão disponíveis em 8000 e a mesma sessão/eventos persistem entre réplicas, sem estado do portal.
- Critérios: NFR01-AC01, NFR03-AC01, NFR04-AC01.

### SI10.4 — Publicar contratos tipados com persistência ORM

- Tipo: comportamento.
- Depende de: SI10.2, SI01.8 e contrato de seis rotas.
- Ações: manter routers finos, controller, validators, repositories e serializers na API acadêmica; mapear domínio, sessões e confirmações por models declarativos; declarar respostas 404/409/422/429/503 sem alterar as seis rotas; preparar tabelas somente no comando init.
- Testes: conferir OpenAPI contra schemas reais; repetir protocolo e garantias em SQLite e PostgreSQL; disputar área/data entre réplicas e repetir decisões consumidas; provar ausência de DDL durante serve.
- Critérios: F10-AC01, F10-AC03, F10-SEC01, NFR01-AC01, NFR03-AC01, NFR04-AC01.
