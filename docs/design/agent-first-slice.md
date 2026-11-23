# Agente — primeira fatia: sessão e leitura segura

## Objetivo didático

Antes de colocar um modelo na conversa, provar que a ferramenta sabe **de quem é a sessão** e **o que ela pode consultar**. Relaciona-se a F09/SI09.1 e SI09.2. Esta fatia não conclui F09 e não altera o estado de indisponibilidade do chat.

## Fluxo

1. A API autentica o morador, como já faz hoje.
2. A composição cria `SessionIdentity.from_authenticated_actor(session_id, actor)` com identidade fornecida pelo servidor. O objeto é imutável; não guarda texto de conversa.
3. `ReservationReadTool` recebe essa identidade. Apenas seu método `list_my_reservations` será registrado no runtime. Ele não aceita apartamento, usuário nem sessão como argumentos do modelo.
4. A chamada revalida o usuário no serviço de identidade e confere sessão, dono e vínculo atual.
5. O repository consulta apenas reservas ativas da unidade daquela sessão e pertencentes ao morador autenticado. O histórico de um antigo titular não é transferido quando a unidade muda de responsável. A consulta SQL repete o vínculo vigente, inclusive quando o mesmo morador possui mais de uma unidade.
6. A projeção retorna dados de reserva em formato JSON, sem identificador privado do morador.

## Onde ler

- `services/agent/tools/reservation_read.py`: identidade e contrato de ferramenta.
- `services/agent/repositories/reservation_tool_repository.py`: consulta com escopo imposto no banco.
- `services/agent/tests/test_reservation_read_tool.py`: nove testes de identidade e fronteiras.
- `services/agent/tests/test_reservation_tool_repository.py`: quatro testes da consulta real com SQLite em memória.

Os testes SQLite comprovam o filtro da leitura. Não comprovam locks, constraints, concorrência de escrita ou compatibilidade completa com PostgreSQL.

## Executar sem modelo e sem credenciais

Na raiz do projeto, em ambiente Python com as dependências instaladas:

```sh
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=packages/microservice-toolkit/src:packages/aurora-toolkit/src:. \
python3 -m unittest discover -s services/agent/tests -v
```

## Exercício para a próxima sessão

Antes de conectar o ADK, explique: por que a função não recebe `apartment`? Por que conferir a identidade apenas quando abre o chat é insuficiente? Por que consultar todas as reservas e filtrá-las depois é pior que filtrar na consulta?

Depois, acompanhe o caso com um morador responsável pelas unidades 101 e 102. A sessão aberta no 101 só pode consultar 101, mesmo que a mensagem peça 102. Remover o vínculo também deve impedir novas leituras.

## Próximas fatias, ainda não implementadas

- Registrar a tool no especialista de reservas e conectar Runner/ADK com sessão/eventos persistidos.
- Agente principal + especialista de reservas + especialista de convivência (visitas/regulamento), como proposto na F09; validar topologia para retomada de confirmação antes de fechar a decisão.
- Busca seletiva do regulamento.
- Escrita e confirmação externa persistida, aprovação/negação/reenvio/reinício.
- Adaptador acadêmico F10 e seus quinze passos de avaliação.

Não há chamada a Gemini, gravação de reservas, novas rotas, migração ou alteração de credenciais nesta fatia. O adaptador acadêmico precisará criar um contexto próprio e isolado; não deve simular uma autenticação de produção inexistente.
