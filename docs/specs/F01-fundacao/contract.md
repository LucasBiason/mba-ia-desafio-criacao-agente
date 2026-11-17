# Contrato de verificação — F01 — Fundação executável

## Pré-requisitos

Prepare uma composição isolada e uma massa de dados de demonstração. No cenário de base, use o processo de inicialização do README e registre revisão, resposta e resultado observado. No cenário de aula ou de avaliação, verifique antes a disponibilidade das ferramentas, sessão persistida e credencial de execução externa autorizada. Os dados de origem permanecem intactos.

## Itens

- **E2E-F01-01** (P0D, cobre F01-AC01) — Um clone com Docker e o cliente Compose e os dados iniciais. Validar o manifesto, subir a composição de teste, conferir serviços saudáveis e abrir a origem publicada -> A composição inicia as onze unidades e carrega a tela de login. Modo: Base.
- **E2E-F01-02** (P0D, cobre F01-AC02) — Uma configuração obrigatória de autenticação ausente numa composição descartável. Omitir a configuração em sandbox e comparar status do serviço e saída sanitizada -> O Compose recusa a configuração ou a autenticação fica sem prontidão. A falha identifica a variável sem divulgar segredo. Modo: Base.
- **E2E-F01-03** (P0D, cobre F01-AC03) — Uma edição persistida em volume existente. Criar uma conta e alterar um cadastro, reiniciar os serviços e consultar os dois pelas mesmas APIs -> A edição continua após reiniciar e a carga inicial não a sobrescreve. Modo: Base.
- **E2E-F01-04** (P0D, cobre F01-SEC01) — Um cliente na origem publicada. Consultar a superfície pública de desenvolvimento e confirmar que a rota interna não está exposta -> O proxy expõe caminhos públicos e privados esperados e mantém as rotas internas fechadas. Modo: Base.
- **E2E-F01-05** (P0D, cobre NFR02-AC01) — Reinício da dependência, corrida de gravação ou falha antes de concluir a escrita. Comparar estado e resposta da operação em volume isolado. Induzir concorrência quando a funcionalidade tiver disputa de escrita -> Efeito confirmado permanece. A falha é observável e o domínio fica consistente. Modo: Base.
- **E2E-F01-06** (P0D, cobre NFR04-AC01) — Execução da base ou execução isolada do protocolo acadêmico. Executar o procedimento aplicável a partir de uma instalação isolada e registrar componentes, saídas e condições não exercitadas -> As dependências do modo escolhido atingem prontidão e os verificadores registram a condição observada. Modo: Base.

- **E2E-F01-07** (P0D, cobre F01-AC04) — Configurar aplicações com a biblioteca e enviar chamadas válidas, sem identidade e com dados inválidos -> Correlação presente, erro sanitizado e logs sem credenciais ou payloads. Modo: testes HTTP da biblioteca e API real em QA.
- **E2E-F01-08** (P0D, cobre F01-AC05) — Executar importador com cadastros ausentes e repetir a execução -> Cadastros criados por API, repetição sem duplicações e JSONs originais intactos. Modo: API real em QA.

- **E2E-F01-09** (P0D, cobre F01-AC06) — Construir os oito serviços, executar o gate de camadas e consultar health, Swagger e OpenAPI -> Cada domínio tem camadas e modelos ORM próprios, health fornecido pelo toolkit e contratos documentados. Modo: AST e HTTP em QA.

## Cobertura

| Item | Critério | Etapa da prova |
| --- | --- | --- |
| E2E-F01-01 | F01-AC01 | Base |
| E2E-F01-02 | F01-AC02 | Base |
| E2E-F01-03 | F01-AC03 | Base |
| E2E-F01-04 | F01-SEC01 | Base |
| E2E-F01-05 | NFR02-AC01 | Base |
| E2E-F01-06 | NFR04-AC01 | Base |

| E2E-F01-07 | F01-AC04 | Base |
| E2E-F01-08 | F01-AC05 | Base |

| E2E-F01-09 | F01-AC06 | Base |
