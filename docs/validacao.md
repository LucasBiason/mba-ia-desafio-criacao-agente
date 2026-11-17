# Validação da base

Os [dez contratos](specs/index.md) identificam a etapa e a prova exigida por cenário. Esta página registra os resultados observados na base, os recortes ainda não exercitados e o trabalho da aula.

## Resultados observados

| Superfície | Operação verificada | Resultado |
| --- | --- | --- |
| Documentação | MiniBrain valida PRD e executa lint estrito com template obrigatório em cada pacote | PRD aprovado. As dez specs, planos e contratos passaram no gate estrutural. |
| Dados iniciais | Comparação de SHA-256 de cada arquivo com a revisão de origem | Os cinco arquivos de dados coincidem com a origem. |
| Composição | Partida em ambiente Compose separado com build e espera de saúde | Web, autenticação, usuários, condomínio, agente e os dois bancos ficaram saudáveis. A prontidão do agente comprova a fronteira de integração. A consultoria não está configurada. |
| Proxy e identidade | Teste integrado de saúde, autenticação, papel e endpoints internos | A saúde da API respondeu. A API privada recusou ausência de sessão e bloqueou o morador em rotas administrativas. A introspecção permaneceu fora do proxy público. |
| JWT e saída | Sessão de morador, token alterado, erro de entrada e logout por HTTP | Perfil corrente retornou. Token alterado e sessão após logout foram recusados com 401. A resposta de validação omitiu a entrada usada no teste. |
| Contas e apartamentos | Conferir usuários importados, atribuir responsável, renumerar unidade e testar a proteção do último administrador | Os nomes da fonte corresponderam aos usuários moradores. O código interno permaneceu ao mudar o número. Foram recusadas a alteração de papel, a desativação da última administração e a exclusão de unidade com histórico. |
| Áreas e agenda | Criar área gratuita, rejeitar taxa negativa, editar e excluir área, filtrar reserva | A rota administrativa preservou as referências de histórico. O acesso de morador para alteração foi recusado. O filtro trouxe somente as reservas da área selecionada. |
| Horários de reservas e de visitas | Preencher, consultar, limpar e testar horários inválidos, incluindo saída da visita sem entrada | A atualização preservou código, unidade, data e titularidade. Somente o administrador conseguiu alterar os horários e uma reserva de horário informado apareceu com os mesmos valores para o titular. |
| Regulamento | Publicar, recusar base já ultrapassada e confirmar versão anterior | A publicação incrementou a versão, registrou o autor e preservou a revisão anterior. O morador consultou a versão vigente e teve escrita negada. |
| Domínio isolado | Publicações concorrentes e reinício sobre PostgreSQL descartável | A concorrência produziu um HTTP 200 e um 409. O histórico foi preservado após reinício do domínio. |
| Reservas, visitas e chat | Consultas próprias, tentativa de outra unidade, criação e leitura de sessão, envio ao agente ainda não configurado | A API limitou as projeções à unidade autorizada. Abriu a sessão com 201 e a retomou em seguida. O envio devolveu 503 com `AGENT_NOT_CONFIGURED` e a comparação confirmou as mesmas reservas antes e depois. |
| Interface Chromium | Jornadas de administração e morador no mesmo ambiente QA, em 1440×900 e 390×844 | Login, logout, painel, cadastro e inativação de conta, criação, edição e exclusão de apartamento e área, agenda, visitas, publicação e histórico do regulamento executados. No morador, menu condicionado ao papel, sessão de chat legível após recarregar e indisponibilidade 503 foram observados. As execuções ficaram sem exceções JavaScript e sem transbordamento horizontal. |
| Calendário e horários no Chromium | Selecionar Quadra, buscar `RSV-4821` de outra área, registrar e limpar horários de uma reserva e de uma visita | A busca selecionou Salão de Festas e 16/03/2030, com o nome do morador responsável no dia. Os horários editados apareceram nas tabelas e voltaram a **Não informado** após a limpeza. O calendário móvel coube na largura da tela. |
| Calendário mensal com massa de teste | Carregar as três áreas, abrir dias cheios e vazios, navegar por setas, voltar a hoje, buscar por código e editar os horários de uma reserva de teste | Em 1440 e 390 px, a lista abriu no dia correto. Em um dia com três reservas, **+N** abriu as três. A busca saltou para a área e a data do registro, e Escape fechou a lista. O seletor móvel abriu inteiro na tela. |
| Carga removível para a agenda | Reexecutar a carga no playground e testar a remoção em PostgreSQL isolado | A agenda local recebeu 278 reservas. A segunda execução inseriu zero registros. A comparação preservou as três reservas de origem. Na base descartável, a remoção preservou códigos e ocupações de fora da carga. |
| Falha fechada de autenticação | Parar apenas o serviço auth na instância descartável e consultar usuários e áreas com bearer que era válido | As duas APIs privadas responderam 503 durante a indisponibilidade de identidade. Após o teste, o serviço retornou à composição. |
| Reinício integral | Capturar a saída das APIs, parar os sete serviços e iniciar novamente por Compose com espera de prontidão | Contas, versão vigente e histórico, reservas, visitas e sessão de chat permaneceram iguais nas respostas comparadas. |
| Configuração obrigatória | Validar a composição num cenário de teste sem o arquivo local de configuração | O Compose recusou a inicialização sem a configuração obrigatória. |

Os nove testes de API foram executados pela origem Nginx no ambiente isolado de QA, com `AURORA_URL=http://127.0.0.1:8768 python3 -B tests/test_api.py`. Os testes de domínio em PostgreSQL real também conferiram instalação inicial, migração, reinício, preservação de vínculos existentes e titularidade das reservas e visitas após troca de responsável. A [prova de runtime](../tests/test_runtime.py) exercita a parada de autenticação e o reinício integral após a suíte de API, na mesma instância descartável.

A instância de uso em 8767 foi atualizada com os volumes existentes. A comparação antes e depois confirmou os mesmos números de apartamento, reservas, visitas e versões do regulamento, além da preservação do acesso inicial. Os seis apartamentos provenientes da carga ficaram associados aos usuários moradores. Os cadastros e edições feitos durante os testes ficaram na composição de QA.

## Reproduzir

Use os [comandos de partida e teste da base](../README.md) para executar a suíte sem misturar a massa com o ambiente de uso. As condições de cada teste estão nos [contratos](specs/index.md). Depois do teste de API, execute `AURORA_URL=http://127.0.0.1:8768 python3 -B tests/test_runtime.py` na composição descartável correspondente. O teste para os serviços de QA para medir recuperação e preservação do estado.

Com o diretório do MiniBrain selecionado em `MINIBRAIN_ROOT`, estes comandos verificam novamente a estrutura:

```sh
python3 -B "$MINIBRAIN_ROOT/.harness/skills/sdd-prd/scripts/validate_prd.py" docs/prd
for feature in docs/specs/F*; do
  python3 -B "$MINIBRAIN_ROOT/.harness/skills/sdd-spec/scripts/lint_spec.py" "$feature" --strict --require-template || exit
done
```

## Cobertura ainda dependente de execução

- A expiração controlada de token e a comparação das respostas em tentativas de login têm casos próprios no [contrato de autenticação](specs/F03-autenticacao/contract.md).
- Os testes por HTTP cobrem as operações e recusas indicadas acima. A conferência visual acima cobre os dois tamanhos e as jornadas listadas. Casos de recuperação por falhas não induzidas nesta rodada permanecem como cenário de contrato.
- Aulas de orquestração, consulta por tools, autorização de visita, reserva, confirmação, retomada e corrida de aprovações seguem o [roteiro do agente](roteiro-agente.md).
- A entrada separada na porta 8000 e os 15 passos do avaliador dependem da prática do agente e do [adaptador acadêmico](specs/F10-avaliacao/spec.md).

Registre revisão, operação e resultado observado para cada nova prova. Credenciais e tokens ficam fora das saídas publicadas.

## Revisão documental da primeira entrega

A [matriz consolidada](entrega-01.md) liga implementação, evidência disponível e pendências. F11–F14 individualizam navegação, painéis e perfil. As evidências históricas acima permanecem identificadas como execuções anteriores. A atualização de documentação não reexecuta os testes destrutivos de runtime no ambiente de uso.

## Branch integrada do fork

A nova execução de build, nove testes HTTP e runtime foi concluída no checkout do fork, em Compose isolado na porta 8768. A composição preservou os dados após reiniciar e recusou as APIs privadas quando a autenticação ficou indisponível. Consultar [a primeira entrega](entrega-01.md) para ambiente, recorte e publicação pendente.

A navegação da branch foi validada com API real no Chromium em 1440 e 390 px para os dois perfis, incluindo login, todas as rotas, perfil, saída e busca por código na agenda. Não foram observadas exceções JavaScript ou rolagem horizontal de página. O aviso de integração pendente do assistente é o comportamento especificado.
