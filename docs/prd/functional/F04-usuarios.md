# F04 — Gestão de usuários e perfis

Domínio: Administração | Onda: 3 | Prioridade: 1

Conforms to: NFR01, NFR03

## Descrição

Cadastrar, editar, desativar e consultar usuários dos tipos Administração e Morador, sem expor credenciais. O papel é definido na criação da conta.

Como administrador, quero criar perfis de moradores e corrigir seus dados para manter os acessos do residencial.

A referência de produto original é FR04. A correspondência dos critérios anteriores é F04-AC01 ↔ FR04/AC01, F04-AC02 ↔ FR04/AC02, F04-AC03 ↔ FR04/AC03. Critérios adicionais descrevem verificações específicas desta separação de etapas.

## Capacidades

- Consumes: F03.
- Provides: Perfis públicos com identificador, nome, email, papel e estado e uma consulta interna controlada para vincular moradores.
- Integração: CRUD de contas passa pelo proxy e chega a `users`. A API resolve a identidade e exige o papel administrativo antes de persistir em `identity-db`. O cadastro de apartamentos usa somente a projeção pública para confirmar que a conta é elegível.

## Comportamento esperado

- **Dado** um administrador autenticado e dados de um novo morador
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** o cadastro devolve perfil público, aceita login da nova conta e permite vinculá-la.

- **Dado** o último administrador ativo sofre tentativa de desativação
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** a operação é recusada e uma conta administrativa continua ativa.

- **Dado** um morador com sessão válida tenta acessar outro perfil ou a lista administrativa
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** a resposta não inclui registros alheios.

- **Dado** uma conta existente
- **Quando** o operador exercita o cenário descrito na verificação
- **Então** edição persiste e a desativação invalida o acesso; duplicidade é rejeitada.

## Critérios de aceite

| ID | Condição | Resultado esperado | Como verificar |
| --- | --- | --- | --- |
| F04-AC01 | Um administrador autenticado e dados de um novo morador | O cadastro devolve perfil público, aceita login da nova conta e permite vinculá-la | Criar a conta pelo painel, autenticar, confirmar formato público e vincular unidade |
| F04-AC02 | O último administrador ativo sofre tentativa de desativação | A operação é recusada e uma conta administrativa continua ativa | Em ambiente isolado, desativar as outras contas administrativas e tentar desativar a última |
| F04-AC03 | Um morador com sessão válida tenta acessar outro perfil ou a lista administrativa | A resposta não inclui registros alheios | Pedir lista administrativa e perfil próprio e inspecionar apenas a identidade autenticada |
| F04-AC04 | Uma conta existente | Edição persiste e a desativação invalida o acesso; duplicidade é rejeitada | Atualizar uma conta criada para o teste, repetir email em segunda conta, desativar e reapresentar token |

A etapa de cada prova está identificada na [spec desta funcionalidade](../../specs/F04-usuarios/spec.md#7-estratégia-de-testes).

## Segurança

| ID | Dimensão | Critério | Como verificar |
| --- | --- | --- | --- |
| F04-SEC01 | Fronteiras e escopo | O JSON e a evidência não incluem senha ou hash | Inspecionar respostas válidas e de erro com credenciais descartáveis |

## Fora do escopo

Autocadastro, distribuição automática de convites, recuperação de senha por email e exclusão física de contas com histórico.

## Tratamento de erros

Email duplicado causa conflito. Campo inválido retorna mensagem por campo. Tentativas de alterar o papel ou desativar a última conta administrativa ativa retornam conflito. Conta desativada perde acesso validado.
