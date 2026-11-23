<div align="center">
  <img src="branding/banner.svg" alt="Residencial Aurora — Regra é regra" width="100%" />
  <br /><br />
  <img src="branding/logo.svg" alt="Logo do Residencial Aurora" width="88" />
</div>

# Residencial Aurora

Assistente virtual para reservar áreas comuns, cancelar reservas do próprio apartamento, autorizar visitantes e consultar o regulamento do condomínio. Projeto do desafio **Regra é regra**, do MBA de IA da Full Cycle.

![Python 3.12 ou superior](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-depend%C3%AAncias-6340AC?style=flat-square&logo=uv&logoColor=white)
![Google ADK série 2](https://img.shields.io/badge/Google_ADK-s%C3%A9rie_2-4285F4?style=flat-square&logo=google&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-modelo-5268D6?style=flat-square&logo=googlegemini&logoColor=white)

**Status:** o modo acadêmico tem API e agentes separados do produto. Os testes locais com o ADK e modelo simulado não substituem a validação com Gemini. O portal administrativo é um complemento de portfólio e não é necessário para o avaliador.

## Arquitetura

Na avaliação, FastAPI recebe a mensagem, recupera o apartamento fixo da sessão e passa o turno ao Runner do Google ADK. O **principal** encaminha a conversa por transferência nativa do ADK, na mesma sessão persistida. **Reservas** consulta disponibilidade e reservas próprias, cria reservas e cancela reservas próprias. **Convivência** lê e autoriza visitas e consulta um artigo do regulamento. A divisão mantém ferramentas de agenda separadas das de convivência; o servidor, não o modelo, define a unidade de todas as tools.

```text
Cliente → API acadêmica → Runner ADK → principal → especialista → tool → SQLite
                        ↘ histórico ADK               ↳ pedido de confirmação
Cliente → POST /sessoes/{session_id}/confirmacoes → retoma a execução do especialista
```

O modo acadêmico usa dois arquivos SQLite locais: registros do domínio/pendências e sessões/eventos do ADK. Não depende do Docker, PostgreSQL ou credenciais do portal. A interface administrativa usa composição, autenticação e dados próprios.

## Garantias

| Garantia | Implementação acadêmica |
| --- | --- |
| **1. Aprovação fora do chat** | [tools de reserva e visita](services/agent/academic/runtime.py#L20-L95) chamam `request_confirmation` do ADK. A API [registra a pendência](services/agent/academic/api.py#L235-L301) e [retoma a invocação original](services/agent/academic/api.py#L555-L666) só após a decisão na rota. Negar não grava; repetir recebe 409. |
| **2. Apartamento fixo** | A [criação da sessão](services/agent/academic/api.py#L503-L517) grava o vínculo e [a API resolve a unidade](services/agent/academic/api.py#L100-L107) no servidor. As [tools vinculadas](services/agent/academic/domain.py#L391-L407) não aceitam apartamento escolhido pelo modelo. A consulta de disponibilidade não identifica quem reservou. |
| **3. Persistência** | [DatabaseSessionService](services/agent/academic/api.py#L44-L64) mantém sessões e eventos, e a [rota de eventos](services/agent/academic/api.py#L669-L678) lê os eventos armazenados. O [schema de sessões e confirmações](services/agent/academic/api.py#L30-L41) persiste vínculos e pendências; o [schema de domínio](services/agent/academic/domain.py#L14-L33) mantém efeitos e recibos. Reiniciar com o mesmo diretório conserva os dois bancos. |
| **4. Regulamento sob demanda** | A [tool de convivência](services/agent/academic/runtime.py#L97-L103) chama o [seletor de trechos](services/parameters/queries/regulation_excerpt.py) e usa apenas o artigo pertinente. O texto inteiro não entra no prompt principal nem na ferramenta. Pesquisa ambígua não injeta trecho de outro assunto. |
| **5. Uma reserva ativa por área e dia** | O [índice único parcial](services/agent/academic/domain.py#L14-L33) impede duplicação no armazenamento, e a [inserção](services/agent/academic/domain.py#L228-L243) resolve o conflito como indisponibilidade. O [efeito e recibo](services/agent/academic/domain.py#L195-L225) são tratados na mesma transação; cancelar não libera o código histórico. |

A API acadêmica é local e não autenticada por definição do desafio. Não exponha a porta 8000 na rede. Use um processo por diretório SQLite; a composição com PostgreSQL coordena réplicas no banco. Após uma confirmação interrompida, um novo turno reconcilia o resultado pelo recibo durável ou encerra a tentativa sem executar de novo. Vínculo ou recibo inconsistentes mantém a sessão bloqueada. O reenvio do mesmo ID não repete a ação. Se o evento da proposta foi salvo, mas ela não entrou no índice de pendências, a aprovação explícita pode recuperá-la dos 100 eventos mais recentes da mesma sessão. A API não executa nada só por recuperar a proposta.

## Como rodar

Pré-requisitos: Python 3.12+, `uv` e uma chave do **Google AI Studio**. O Google ADK é fixado em `2.9.1` no projeto. Use os cinco arquivos originais de `dados/`; o aplicativo não os altera.

```sh
cp -n .env.example .env
# Preencha GOOGLE_API_KEY no arquivo .env local; nunca versione a chave.
uv sync --locked
uv run --locked python -m services.agent.academic init
uv run --locked --env-file .env python -m services.agent.academic serve
```

Acesse [`localhost:8000/docs`](http://localhost:8000/docs). `AURORA_MODEL` é opcional (padrão: `gemini-3.5-flash-lite`). Se o Google AI Studio não disponibilizar esse modelo ao projeto da sua chave, configure em `AURORA_MODEL` um modelo Gemini habilitado no projeto. O transporte usa o Google AI Studio, não Vertex AI. As seis rotas e os formatos estão no [enunciado](docs/enunciado.md#contrato-da-api).

**Restaurar sem apagar a sessão anterior:** pare a instância local, escolha um diretório acadêmico novo e inicie usando o mesmo diretório nos dois comandos. Essa instância contém novamente os dados das fixtures e não tem o histórico da instância anterior.

```sh
uv run --locked python -m services.agent.academic restore --data-dir .aurora-academic-restaurado
uv run --locked --env-file .env python -m services.agent.academic serve --data-dir .aurora-academic-restaurado
```

Para testar depois de um reinício, não rode `restore`: volte com `serve` e o diretório anterior. Veja o [tutorial de demonstração](docs/design/aurora-roteiro-do-avaliador.md) para acompanhar uma ação do chat à transação. A bateria local com modelo simulado usa bancos descartáveis:

```sh
PYTHONPATH="$PWD:$PWD/services/agent/tests" uv run --locked python -m unittest discover -s services/agent/tests
```


O [portal autenticado e administrativo](docs/design/portal-bonus.md) é um bônus de portfólio. Frontend, autenticação, pagamento real e deploy não são requisitos da API acadêmica. Para conferir o aceite oficial, siga o [enunciado e os 15 passos](docs/enunciado.md#fluxo-do-avaliador).
