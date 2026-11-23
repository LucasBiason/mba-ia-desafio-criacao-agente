# F09: primeira conexão ao Runner

## Marco de aprendizagem
A tool anterior conhece identidade e domínio; o Runner decide quando chamá-la.
`runtime/read_runner.py` injeta modelo e serviço de sessão explicitamente, expõe
uma única tool sem argumentos de identidade e executa sua rotina síncrona numa
thread. O modelo não escolhe unidade, morador ou sessão. Não há conexão HTTP,
Gemini, segredo ou mudança no contrato acadêmico nesta fatia.

Instale `services/agent/requirements-adk-probe.txt` num ambiente de teste isolado,
com as dependências do projeto. Rode unittest em services/agent/tests com os
pacotes locais no PYTHONPATH. Os seis testes ADK usam fake e SQLite descartável;
sem a dependência, ficam explicitamente skipped. Os testes existentes permanecem
independentes do ADK. A dependência do deploy/uv.lock ainda não foi alterada.

## Experimento executado em 18/11/2026
ADK 2.9.1, Python 3.12.3, DatabaseSessionService SQLite, modelo fake sem rede.
Leitura bound funcionou. Confirmação foi gravada, processo encerrado e novo
processo retomou a tool com sucesso, com resumability desligado e ligado
(neste caso com invocation_id). Recusa não executou o efeito.

**Replay executou novamente o efeito nos dois modos.** ADK não garante consumo
único da confirmação. A rota futura deve manter ledger transacional próprio,
validar dono/sessão/ID, garantir idempotência do efeito e retornar 409 para replay.
Não conectar tools de escrita antes dessa proteção. Também falta testar a
retomada na topologia principal + dois especialistas e PostgreSQL.

A instalação google-adk[db] com SQLAlchemy 2.1.9 não incluiu greenlet. Foi
necessário sqlalchemy[asyncio]; sem isso o ADK reportou NameError enganoso para
create_async_engine depois de ocultar ImportError. Fixar/validar o lock completo
antes de integrar ao deploy, em vez de atualizar dependências compartilhadas.

## Próximo marco
Revisar a separação entre sessão de domínio e sessão ADK. Ligar o runtime de
leitura ao serviço somente após decidir configuração explícita do provedor e
tratamento dos eventos/erros. Depois montar a topologia exigida e implementar
ledger/retomada com testes de recusa, replay, concorrência e reinício. Esta classe
é uma fundação testada, não o agente acadêmico completo nem um chat já disponível.

## Revisão de autorização
Cada mensagem revalida identidade, papel, sessão e vínculo ANTES de chamar o
Runner, inclusive quando o modelo responde direto do histórico sem tools. A
tool revalida novamente no momento da consulta. Testes cobrem desativação,
troca de identidade/papel e revogação do vínculo, sem acesso ao Runner ou novos
eventos nesses casos. A criação da sessão ADK também passa pelo mesmo gate.

## Marco API em modo teste
A rota interna existente agora aceita dependency override `message_handler`.
Sem override continua retornando AGENT_NOT_CONFIGURED/503, sem importar ADK.
Não há flag que ative modelo real. A rota pública e seu contrato permanecem.

O adaptador ReadOnlyMessageHandler revalida usuário, sessão e apartamento do
payload interno antes de carregar sessão ADK; recupera ou cria a sessão sob o
par usuário/sessão e chama o runtime, que revalida novamente. Somente texto
final retorna em `message`; eventos e argumentos de tools não são publicados.
Esse formato interno de teste não implementa nem redefine o contrato F10.

Quatro testes percorrem API pública → controller → fronteira HTTP interna →
Runner → tool. Verificam histórico persistido e isolado, chamadas repetidas,
sessão/usuário/unidade indevidos, revogação e 503 desativado. Transporte usa
TestClient, domínio/identidade são dublês, persistência ADK é SQLite temporário.
O guard interno usa token sintético injetado: estes testes não substituem QA
Docker/JWT real. Nenhum Gemini, segredo ou dado do condomínio foi usado.

A integração aguarda revisão. Ainda faltam serialização de mensagens concorrentes
por sessão, limite de execução do modelo, tratamento final dos eventos/erros,
topologia completa, confirmação transacional e validação PostgreSQL/deploy.

## Disputa entre mensagens da mesma sessão
O adaptador agora transforma StaleSessionError do ADK em HTTP 409 com código
CHAT_SESSION_CONFLICT. O controller público preserva apenas esse erro conhecido,
com mensagem sanitizada. Não reexecuta automaticamente Runner/modelo/tool e não
usa um lock em memória como se protegesse múltiplos processos.

O teste usa dois DatabaseSessionService independentes sobre o mesmo SQLite,
com barreira determinística antes de gravar respostas. Resultado: uma resposta
válida e um 409; duas mensagens de entrada e uma resposta ficam preservadas.
Uma tentativa explícita posterior carrega o estado atual e funciona. Outro teste
verifica o 409 através da API pública e confirma ausência de repetição automática.

Limite importante: isso é conflito otimista observável, não serialização completa
nem transação de uma conversa inteira. A mensagem de entrada do pedido que
falhou pode já estar persistida, e a inferência pode já ter ocorrido. Não prometer
rollback integral, execução única ou ausência de custo em produção. Antes de
habilitar tools de escrita é obrigatório ledger/idempotência de domínio; antes
de produção, verificar PostgreSQL e concorrência em processos reais. O teste de
instâncias independentes prova ausência de dependência de lock compartilhado,
mas não substitui essa validação multiprocessos.

## Wiring opt-in do provedor, ainda desativado
`runtime/configuration.py` oferece AgentRuntimeSettings e configure_read_agent.
O deploy atual NÃO chama essa função: continua 503 por padrão. A rota interna
consulta app.state, além de permitir override em teste. Importar a configuração
não acessa ambiente/segredos e não importa ADK enquanto desativada.

Para futura composição autorizada, informar enabled=True, nome explícito do
modelo Gemini AI Studio e banco ADK persistente, mais um credential_provider
fornecido pelo responsável pelo deploy. A composição exige ADK exatamente2.9.1.
A credencial só é solicitada após autorização da primeira mensagem; não é campo
serializável de settings. Gemini usa vertexai=False e não recebe endpoint livre.
Cliente/modelo é reutilizado, persistência e cliente são fechados no lifespan.

Limites: no máximo4 chamadas LLM por execução, timeout HTTP15s, attempts=1 no
cliente e timeout60s no adaptador. Timeout não desfaz eventos já persistidos.
Esses limites reduzem risco, mas NÃO são teto financeiro. Não garantem que uma
requisição cancelada não seja faturada. Nenhum nome de modelo concreto ou preço
foi escolhido para produção; validar disponibilidade e orçamento antes de ativar.

Testes usam chave sintética e construtor Gemini mockado, sem conexão externa.
Não lemos nenhuma credencial real. A ativação real permanece uma etapa distinta:
exige decidir modelo/cota, destino autorizado dos dados, secret provider,
dependências/lock, banco PostgreSQL e operação. O código é wiring testável,
não uma afirmação de que Gemini já esteja conectado ou aprovado em produção.

## Revisão: destino e latência
O Gemini recebe base_url fixo https://generativelanguage.googleapis.com tanto
no ADK quanto nas opções do SDK. Clientes httpx próprios têm trust_env=False,
verify=True e follow_redirects=False; hooks bloqueiam esquema, host ou porta
fora do destino permitido antes de enviar. Assim proxy/CA ambientais não são
herdados, sem desligar TLS. SDK usa esses clientes em vez de aiohttp. Ambiente
corporativo que exige proxy/CA customizada precisa de configuração revisada;
esta composição falha fechada, não contorna a exigência de rede.

O transporte público→agente agora tem leitura65s, acima do limite interno60s,
conexão/escrita/pool3s. Outras chamadas de identidade continuam3s. Não há retry
automático. Proxy frontal/browser podem ter limites próprios ainda não validados;
cancelamento do cliente não prova interrupção do processamento ou ausência de
cobrança. Aumentar timeout não resolve idempotência: mensagem/efeito precisam de
controle próprio antes das próximas etapas de produção/escrita.

Testes incluem SDK real com chave fictícia e conexão TCP bloqueada: override
GOOGLE_GEMINI_BASE_URL/proxy não muda destino nem transporte. Nenhuma geração
foi executada e nenhuma credencial real foi lida.

## Revisão adicional: SDK CA e proxy frontal
O SDK também cria contextos SSL antes de usar os clientes injetados. Agora recebe
SSLContext explícito em client_args.verify e async_client_args.verify/ssl,
construído com o bundle certifi explícito. Assim SSL_CERT_FILE/SSL_CERT_DIR não
alteram nem quebram a inicialização. TLS mantém CERT_REQUIRED, hostname checking
e CAs carregadas. Teste constrói o SDK real com caminhos CA inexistentes,
endpoint/proxy hostis e bloqueio TCP: passou, sem geração.

Nginx ganha timeout75s exclusivamente para as rotas de mensagens, incluindo o
alias /services/agent; as demais rotas continuam15s. proxy_next_upstream off evita
repetição pelo proxy. Ordem das locations e orçamentos são testados. nginx -t
passou em contêiner descartável, sem rede, configuração somente leitura. Não foi
feito redeploy nem teste de latência real de75s; navegador ainda deve ser validado.
